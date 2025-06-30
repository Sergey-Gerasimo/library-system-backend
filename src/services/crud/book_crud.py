from typing import Optional, Protocol
from abc import abstractmethod
from sqlalchemy import select, delete, update, and_
from uuid import UUID

from services.abc import AbstractCRUD, ICRUD
from services.exceptions import handle_db_errors
from models import Book as Model
from schemas import (
    BookCreate as Create,
    BookFilter as Filter,
    BookInDB as Response,
    BookUpdate as Update,
)


class IBookCRUD(ICRUD["Response", "Create", "Update", "Filter"], Protocol):
    """Протокол для типизации CRUD операций с книгами.

    Расширяет базовый интерфейс ICRUD специфичными методами для работы
    с книгами. Определяет контракт для всех реализаций сервиса книг.

    Методы:
        get_by_title: Поиск книги по точному названию
        get_by_author: Получение всех книг автора

    Типы:
        Response: BookInDB - схема ответа с данными книги
        Create: BookCreate - схема создания книги
        Update: BookUpdate - схема обновления книги
        Filter: BookFilter - схема фильтрации книг
    """

    async def get_by_title(self, title: str) -> Optional[Response]:
        """Находит книгу по точному совпадению названия.

        :param title: Полное название книги для поиска
        :type title: str
        :return: Найденная книга или None
        :rtype: Optional[BookInDB]
        """
        ...

    async def get_by_author(self, author_id: UUID) -> list[Response]:
        """Получает все книги, принадлежащие указанному автору.

        :param author_id: Идентификатор автора
        :type author_id: UUID
        :return: Список книг автора
        :rtype: List[BookInDB]
        """
        ...


class BookCRUD(AbstractCRUD[Model, Create, Update, Filter, Response]):
    """Реализация CRUD операций для работы с книгами.

    Наследует базовые CRUD операции от AbstractCRUD и добавляет
    специализированные методы для работы с книгами:
    - Поиск по точному названию
    - Получение книг автора

    Все методы защищены декоратором @handle_db_errors для обработки ошибок БД.

    Типы:
        Model: Book - SQLAlchemy модель книги
        Create: BookCreate - схема создания книги
        Update: BookUpdate - схема обновления книги
        Filter: BookFilter - схема фильтрации книг
        Response: BookInDB - схема ответа с данными книги

    Пример использования:
        # Инициализация
        book_crud = BookCRUD(db_session)

        # Создание книги
        new_book = await book_crud.create(BookCreate(
            title="Новая книга",
            year=2023,
            author_id=uuid.UUID("..."),
            genre="Фантастика"
        ))

        # Поиск по названию
        book = await book_crud.get_by_title("Новая книга")

        # Получение книг автора
        author_books = await book_crud.get_by_author(author_id)
    """

    @property
    def model(self) -> type[Model]:
        """Возвращает класс SQLAlchemy модели Book.

        Используется в базовых CRUD операциях для взаимодействия с БД.

        :return: Класс модели книги
        :rtype: type[Book]
        """
        return Model

    @property
    def response_schema(self) -> type[Response]:
        """Возвращает Pydantic схему BookInDB для валидации ответов.

        Используется для преобразования объектов БД в Pydantic модели.

        :return: Класс схемы ответа
        :rtype: type[BookInDB]
        """
        return Response

    @handle_db_errors()
    async def get_by_title(self, title: str) -> Optional[Response]:
        """Находит книгу по полному совпадению названия.

        Поиск выполняется по точному регистрозависимому совпадению.
        Для поиска по части названия используйте метод get_all с фильтром.

        :param title: Полное название книги
        :type title: str
        :return: Найденная книга или None
        :rtype: Optional[BookInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        result = await self.db.execute(
            select(self.model).where(self.model.title == title)
        )
        book = result.scalar_one_or_none()
        return self.response_schema.model_validate(book) if book else None

    @handle_db_errors()
    async def get_by_author(self, author_id: UUID) -> list[Response]:
        """Получает все книги указанного автора.

        Возвращает список всех книг, отсортированный по году издания
        (от новых к старым).

        :param author_id: Идентификатор автора
        :type author_id: UUID
        :return: Список книг автора
        :rtype: list[BookInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        result = await self.db.execute(
            select(self.model).where(self.model.author_id == author_id)
        )
        return [self.response_schema.model_validate(b) for b in result.scalars()]
