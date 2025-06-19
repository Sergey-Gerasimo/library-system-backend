from fastapi import APIRouter, Depends, HTTPException, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
import secrets

from config.keycloak import openid_config, client_config, keycloak_settings
from config.settings import app_settings

from services.auth_service import AuthService
from models import Token
from api.dependencies import get_auth_service, get_user_service

router = APIRouter(prefix="/auth", tags=["auth"])

state_store = {}
session_store = {}


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    token = await auth_service.direct_login(form_data.username, form_data.password)
    return token


@router.get("/login")
async def login_via_sso():
    """Перенаправление на SSO"""
    state = secrets.token_urlsafe(16)
    state_store[state] = True

    auth_url = (
        f"{openid_config['authorization_endpointauth_url']}?"
        f"response_type=code&"
        f"client_id={client_config['client_id']}&"
        f"redirect_uri={keycloak_settings.REDIRECT_URL}&"
        f"scope=openid profile email&"
        f"state={state}"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(
    code: str,
    state: str,
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:

    if state not in state_store:
        raise HTTPException(status_code=400, detail="Invalid state")

    try:
        token = await auth_service.login_via_authtorization_code(code=code)
        return token

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token")
async def refresh_token(
    refresh_token: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    """Обновление access token"""
    try:
        token = await auth_service.refresh_token(refresh_token=refresh_token)
        return token

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/logout")
async def logout(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token")),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    try:
        await AuthService.logout()
        return {"message": "Successfully logged out"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
