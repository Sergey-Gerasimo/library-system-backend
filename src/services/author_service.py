from uuid import UUID
from typing import List
from fastapi import HTTPException, status

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Author
from schemas import AuthorCreate, AuthorUpdate


class AuthorService:
    def __init__(self, db_session: AsyncSession):
        """Инициализирует сервис авторов.

        :param db_session: Асинхронная сессия SQLAlchemy
        :type db_session: AsyncSession
        """
        self.db = db_session

    async def create_author(self, author_data: AuthorCreate) -> Author:
        """Создает нового автора в базе данных.

        :param author_data: Данные для создания автора
        :type author_data: AuthorCreate
        :return: Созданный объект автора
        :rtype: Author
        :raises HTTPException: 409 если автор с таким именем уже существует
        :raises HTTPException: 500 при ошибке базы данных
        """
        author = Author(name=author_data.name, bio=author_data.bio)

        try:
            self.db.add(author)
            await self.db.commit()
            await self.db.refresh(author)
            return author
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Author with this name already exists",
            )

    async def get_author_by_id(self, author_id: UUID) -> Author:
        """Получает автора по ID.

        :param author_id: UUID автора
        :type author_id: UUID
        :return: Объект автора с загруженными best_books и books_count
        :rtype: Author
        :raises HTTPException: 404 если автор не найден
        :raises HTTPException: 500 при ошибке базы данных
        """
        try:
            query = (
                select(Author)
                .where(Author.id == author_id)
                .options(
                    selectinload(Author.best_books), selectinload(Author.books_count)
                )
            )

            result = await self.db.execute(query)
            author = result.scalar_one_or_none()

            if not author:
                raise HTTPException(404, "Author not found")

            return author

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )

    async def get_all_authors(self) -> List[Author]:
        """Получает список всех авторов.

        :return: Список объектов авторов
        :rtype: List[Author]
        """
        result = await self.db.execute(select(Author))
        return result.scalars().all()

    async def update_author(self, author_id: UUID, update_data: AuthorUpdate) -> Author:
        """Обновляет данные автора.

        :param author_id: UUID автора для обновления
        :type author_id: UUID
        :param update_data: Данные для обновления
        :type update_data: AuthorUpdate
        :return: Обновленный объект автора или None если не найден
        :rtype: Author
        :raises HTTPException: 404 если автор не найден
        :raises HTTPException: 409 при конфликте уникальности имени
        :raises HTTPException: 500 при ошибке базы данных
        """
        try:
            result = await self.db.execute(select(Author).where(Author.id == author_id))
            author = result.scalar_one_or_none()

            if not author:
                raise HTTPException(404, "Author not found")

            update_values = update_data.model_dump(exclude_unset=True)

            if not update_values:
                return author

            if "name" in update_values:
                existing_author = await self.db.execute(
                    select(Author)
                    .where(Author.name == update_values["name"])
                    .where(Author.id != author_id)
                )
                if existing_author.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Author with this name already exists",
                    )

            for field, value in update_values.items():
                setattr(author, field, value)

            self.db.add(author)
            await self.db.commit()
            await self.db.refresh(author)

            return author

        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Database integrity error"
            )
        except HTTPException:
            raise  # Пробрасываем уже обработанные HTTPException
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )

    async def delete_author(self, author_id: UUID) -> Author:
        """Удаляет автора из базы данных.

        :param author_id: UUID автора для удаления
        :type author_id: UUID
        :return: Удаленный объект автора
        :rtype: Author
        :raises HTTPException: 404 если автор не найден
        :raises HTTPException: 400 если у автора есть связанные книги
        :raises HTTPException: 500 при ошибке базы данных
        """
        author = await self.get_author_by_id(author_id)

        try:
            await self.db.execute(delete(Author).where(Author.id == author_id))
            await self.db.commit()
            return author

        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete author with associated books",
            )
