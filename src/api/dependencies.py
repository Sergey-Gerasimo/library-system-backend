from services.services import (
    GenreService,
    AuthorService,
    AuthService,
    BookService,
    UserService,
    StorageService,
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
from fastapi.exceptions import HTTPException
from config import services_settings, s3_settings

from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from typing import Any, AsyncGenerator

from loguru import logger

_redis_pool: ConnectionPool | None = None


async def init_redis_pool():
    """Инициализация пула соединений при старте приложения"""
    global _redis_pool

    redis_url = f"redis://{services_settings.REDIS_SETTINGS.HOST}:{services_settings.REDIS_SETTINGS.PORT}/{services_settings.REDIS_SETTINGS.DB}"

    connection_kwargs = {
        "decode_responses": True,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
    }

    if services_settings.REDIS_SETTINGS.IS_SSL:
        connection_kwargs["ssl"] = True
        connection_kwargs["ssl_cert_reqs"] = None

    try:
        _redis_pool = ConnectionPool.from_url(redis_url, **connection_kwargs)

        # Проверяем подключение
        async with Redis(connection_pool=_redis_pool) as redis:
            await redis.ping()
        logger.info("Redis connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis pool: {str(e)}")
        raise


async def close_redis_pool():
    """Закрытие пула соединений при завершении приложения"""
    if _redis_pool:
        await _redis_pool.disconnect()


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Корректное получение Redis соединения из пула
    с обработкой ошибок и автоматическим возвратом в пул
    """
    if not _redis_pool:
        raise HTTPException(
            status_code=500, detail="Redis connection pool is not initialized"
        )

    redis = Redis(connection_pool=_redis_pool)
    try:
        yield redis
    except Exception as e:
        logger.error(f"Redis operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to execute Redis operation")
    finally:
        await redis.close()


async def get_s3_crud() -> AsyncGenerator[S3CRUD, Any]:
    s3 = S3CRUD(
        aws_access_key_id=s3_settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=s3_settings.AWS_SECRET_ACCESS_KEY,
        region_name=s3_settings.S3_REGION_NAME,
        bucket_name=s3_settings.S3_BUCKET_NAME,
        endpoint_url=s3_settings.S3_ENDPOINT_URL,
    )

    yield s3


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
    s3: S3CRUD = Depends(get_s3_crud),
) -> AsyncGenerator[BookService, Any]:
    crud = BookCRUD(db_session=db)
    book_files_crud = BookFilesCRUD(db_session=db)
    yield BookService(book_crud=crud, book_files_crud=book_files_crud, s3=s3)


async def get_genre_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[GenreService, Any]:
    crud = GenreCRUD(db_session=db)
    yield GenreService(crud=crud)


async def get_storage_service(
    db: AsyncSession = Depends(get_db),
    s3: S3CRUD = Depends(get_s3_crud),
) -> AsyncGenerator[StorageService, Any]:
    book_file_crud = BookFilesCRUD(db_session=db)

    yield StorageService(
        storage_crud=s3,
        book_files_crud=book_file_crud,
    )
