from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from services.auth_service import AuthService
from services.user_service import UserService
from models import User
from api.dependencies import get_auth_service, get_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/users/me", response_model=User)
async def get_curent_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="token")),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):

    try:
        token_info = await auth_service.verify_access_token(token=token)
        userinfo = await user_service.get_current_user(token)

        return User(
            id=userinfo.get("sub"),
            username=userinfo.get("preferred_username"),
            email=userinfo.get("email"),
            full_name=userinfo.get("name"),
            roles=token_info.get("realm_access", {}).get("roles", []),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
