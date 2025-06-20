from services.auth_service import AuthService
from services.user_service import UserService
from redis.asyncio import Redis

from typing import Any, AsyncGenerator

from config import services_settings


def get_auth_service() -> AuthService:
    return AuthService()


def get_user_service() -> UserService:
    return UserService()


async def get_redis() -> AsyncGenerator[Redis, Any]:

    redis = Redis(
        host=services_settings.REDIS_SETTINGS.HOST,
        port=services_settings.REDIS_SETTINGS.PORT,
        db=services_settings.REDIS_SETTINGS.DB,
        password=services_settings.REDIS_SETTINGS.PASSWORD,
        ssl=services_settings.REDIS_SETTINGS.IS_SSL,
        decode_responses=True,  # для автоматического декодирования в строки
    )
    try:
        yield redis
    finally:
        await redis.close()
