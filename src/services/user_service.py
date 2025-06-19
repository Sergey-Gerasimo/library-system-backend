from fastapi import HTTPException, status
import httpx

from config.keycloak import openid_config


class UserService:
    @staticmethod
    async def get_current_user(access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                openid_config["userinfo_endpoint"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid access token",
                )
            return response.json()
