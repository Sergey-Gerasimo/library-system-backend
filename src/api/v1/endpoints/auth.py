from fastapi import APIRouter, Depends, HTTPException, Form, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
import secrets
from redis.asyncio import Redis
import json
from datetime import timedelta

from config.keycloak import openid_config, client_config, keycloak_settings
from config.settings import app_settings

from services.auth_service import AuthService
from schemas import Token
from api.dependencies import get_auth_service, get_user_service, get_redis

router = APIRouter(prefix="/auth", tags=["auth"])

state_store = {}
session_store = {}


@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    redis: Redis = Depends(get_redis),
) -> Token:

    cache_key = f"token:{form_data.username}:{hash(form_data.password)}"

    # try to find toke in redis
    token = await auth_service.direct_login(form_data.username, form_data.password)

    cached_token = await redis.get(cache_key)
    if cached_token:
        return Token(**json.loads(cached_token))

    # if not exist, create new token
    token = await auth_service.direct_login(form_data.username, form_data.password)

    # save new token to redis
    await redis.setex(
        cache_key,
        timedelta(minutes=5),
        json.dumps(token.model_dump()),
    )

    # save new token to validation
    await redis.setex(
        f"active_token:{token.access_token}",
        timedelta(hours=1),
        token.refresh_token,
    )

    return token


@router.get("/login")
async def login_via_sso(
    redis: Redis = Depends(get_redis),
):
    """redirct to SSO"""
    state = secrets.token_urlsafe(16)

    # save state to Redis for 10 минут
    await redis.setex(
        f"auth_state:{state}",
        timedelta(minutes=10),
        "1",
    )

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
    redis: Redis = Depends(get_redis),
) -> Token:

    if not await redis.exists(f"auth_state:{state}"):
        raise HTTPException(status_code=400, detail="Invalid state")

    await redis.delete(f"auth_state:{state}")

    # chash code in case of multiple requests
    cache_key = f"auth_code:{code}"
    cached_token = await redis.get(cache_key)
    if cached_token:
        return Token(**json.loads(cached_token))

    try:
        token = await auth_service.login_via_authtorization_code(code=code)

        await redis.setex(
            cache_key,
            timedelta(minutes=5),
            json.dumps(token.model_dump()),
        )

        await redis.setex(
            f"active_token:{token.access_token}",
            timedelta(hours=1),
            token.refresh_token,
        )

        return token

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token")
async def refresh_token(
    refresh_token: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
    redis: Redis = Depends(get_redis),
) -> Token:
    """Refresh access token"""

    cache_key = f"refresh_token:{refresh_token}"

    cached_token = await redis.get(cache_key)
    if cached_token:
        return Token(**json.loads(cached_token))

    try:
        token = await auth_service.refresh_token(refresh_token=refresh_token)

        await redis.setex(
            cache_key, timedelta(minutes=5), json.dumps(token.model_dump())
        )

        await redis.setex(
            f"active_token:{token.access_token}",
            timedelta(hours=1),
            token.refresh_token,
        )

        return token

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/logout")
async def logout(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token")),
    auth_service: AuthService = Depends(get_auth_service),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    try:

        await redis.delete(f"active_token:{token}")

        await auth_service.logout()

        remaining_ttl = await redis.ttl(f"active_token:{token}")

        if remaining_ttl > 0:
            await redis.setex(f"blacklist:{token}", remaining_ttl, "1")

        return {"message": "Successfully logged out"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
