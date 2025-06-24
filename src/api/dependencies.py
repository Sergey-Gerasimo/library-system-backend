from services import (
    GenreService,
    AuthorService,
    AuthService,
    BookService,
    S3Client,
    BookStorage,
    UserService,
)
from config import services_settings

from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal

from redis.asyncio import Redis
from typing import Any, AsyncGenerator


async def get_redis() -> AsyncGenerator[Redis, Any]:
    """
    Фнкция подключения к Redis.
    :return: Redis
    """
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


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_auth_service() -> AsyncGenerator[AuthService, Any]:
    yield AuthService()


async def get_book_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AsyncGenerator[BookStorage, Any]:

    book_storage = BookStorage(redis=redis)
    yield BookService(db, book_storage)


async def get_genre_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[GenreService, Any]:

    yield GenreService(db)


async def get_author_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AuthorService, Any]:

    yield AuthorService(db)


async def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[UserService, Any]:
    yield UserService()
