from services.services import (
    GenreService,
    AuthorService,
    AuthService,
    BookService,
    UserService,
)

from services.crud import (
    GenreCRUD,
    AuthorCRUD,
    UserCRUD,
    BookCRUD,
    BookFilesCRUD,
    BookHistoryCRUD,
    S3CRUD,
)
from config import services_settings, s3_settings

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


async def get_author_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AuthorService, Any]:
    crud = AuthorCRUD(db_session=db)
    yield AuthorService(crud=crud)


async def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[UserService, Any]:
    crud = UserCRUD(db_session=db)
    yield UserService(crud=crud)


async def get_book_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[BookService, Any]:
    crud = BookCRUD(db_session=db)
    book_files_crud = BookFilesCRUD(db_session=db)
    s3 = S3CRUD(
        aws_access_key_id=s3_settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=s3_settings.AWS_SECRET_ACCESS_KEY,
        region_name=s3_settings.S3_REGION_NAME,
        bucket_name=s3_settings.S3_BUCKET_NAME,
        endpoint_url=s3_settings.S3_ENDPOINT_URL,
    )
    yield BookService(book_crud=crud, book_files_crud=book_files_crud, s3=s3)


async def get_genre_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[GenreService, Any]:
    crud = GenreCRUD(db_session=db)
    yield GenreService(crud=crud)
