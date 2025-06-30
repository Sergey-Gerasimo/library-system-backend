from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import db_settings

async_engine = create_async_engine(
    db_settings.DATABSE_URL_asyncpg,
    echo=True,
    pool_size=5,
    max_overflow=10,
)


AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Базовый класс для всех таблиц.

    Имплементирует метод __repr__ для отображения в консоли.
    """

    repr_cols_num = 3
    repr_cols = tuple()

    def __repr__(self):
        """Relationships не используются в repr(), т.к. могут вести к неожиданным подгрузкам"""
        cols = []
        for idx, col in enumerate(self.__table__.columns.keys()):
            if col in self.repr_cols or idx < self.repr_cols_num:
                cols.append(f"{col}={getattr(self, col)}")

        return f"<{self.__class__.__name__} {', '.join(cols)}>"


async def create_tables(async_engine: AsyncEngine) -> None:
    """
    Асинхронное создание таблиц в базе данных.

    :param: async_engine - Асинхронный движок БД.(AsyncEngine)
    :return: None
    """

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
