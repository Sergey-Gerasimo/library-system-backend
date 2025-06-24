from uuid import UUID
from typing import List
from sqlalchemy import select, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from models import Genre, Book
from schemas import GenreCreate, GenreUpdate, GenreWithBooks


class GenreService:
    def __init__(self, db_session: AsyncSession):
        """
        Инициализация сервиса жанров.
        :param db_session: Сессия SQLAlchemy для работы с БД
        """
        self.db = db_session

    async def create_genre(self, genre_data: GenreCreate) -> Genre:
        """
        Создание нового жанра.
        :param genre_data: Данные для создания жанра (имя и описание)
        :return: Созданный объект жанра
        """
        new_genre = Genre(**genre_data.model_dump())
        self.db.add(new_genre)
        await self.db.commit()
        await self.db.refresh(new_genre)
        return new_genre

    async def get_genre_by_id(self, genre_id: UUID) -> Genre:
        """
        Получение жанра по ID со связанными книгами.
        :param genre_id: UUID идентификатор жанра
        :return: Объект жанра с книгами
        :raises HTTPException: 404 если жанр не найден
        """
        stmt = select(Genre).where(Genre.id == genre_id)
        result = await self.db.execute(stmt)
        genre = result.scalar_one_or_none()

        if not genre:
            raise HTTPException(404, f"Genre with id {genre_id} not found")

        return genre

    async def get_all_genres(self) -> List[Genre]:
        """
        Получение списка всех жанров.
        :return: Список объектов жанров
        """
        stmt = select(Genre)
        result = await self.db.execute(stmt)
        genres = result.scalars().all()
        return genres

    async def update_genre(self, genre_id: UUID, genre_data: GenreUpdate) -> Genre:
        """
        Обновление данных жанра.
        :param genre_id: UUID идентификатор жанра
        :param genre_data: Данные для обновления (имя и/или описание)
        :return: Обновленный объект жанра
        :raises HTTPException: 404 если жанр не найден
        """
        stmt = (
            update(Genre)
            .where(Genre.id == genre_id)
            .values(**genre_data.model_dump(exclude_unset=True))
            .returning(Genre)
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        updated_genre = result.scalar_one_or_none()

        if not updated_genre:
            raise HTTPException(404, f"Genre with id {genre_id} not found")

        return updated_genre

    async def delete_genre(self, genre_id: UUID) -> bool:
        """
        Удаление жанра по ID.
        :param genre_id: UUID идентификатор жанра
        :return: True если удаление успешно, False если жанр не найден
        """
        stmt = delete(Genre).where(Genre.id == genre_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def get_best_books(self, genre_id: UUID, limit: int = 5) -> List[Book]:
        """
        Получение лучших книг жанра (по дате создания).
        :param genre_id: UUID идентификатор жанра
        :param limit: Максимальное количество книг (по умолчанию 5)
        :return: Список объектов книг
        """
        stmt = (
            select(Book)
            .where(Book.genre_id == genre_id, Book.is_published == True)
            .order_by(desc(Book.created_at))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        books = result.scalars().all()
        return books
