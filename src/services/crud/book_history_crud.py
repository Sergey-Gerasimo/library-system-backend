from typing import Optional, Protocol, List
from sqlalchemy import select, delete, update, and_
from uuid import UUID
from abc import abstractmethod

from services.abc import AbstractCRUD, ICRUD
from services.exceptions import handle_db_errors
from models import BookHistory as Model
from schemas import (
    BookHistoryCreate as Create,
    BookHistoryFilter as Filter,
    BookHistoryInDB as Response,
    BookHistoryUpdate as Update,
)


class IBookHistoryCRUD(
    ICRUD["Response", "Create", "Update", "Filter"],
    Protocol,
):
    """Протокол для типизации CRUD операций с историей изменений книг.

    Расширяет базовый интерфейс ICRUD специфичными методами для работы
    с историей изменений книг. Определяет контракт для всех реализаций
    сервиса истории изменений.

    Методы:
        get_by_book: Получение истории изменений по ID книги
        get_by_user: Получение истории изменений по ID пользователя

    Типы:
        Response: BookHistoryInDB - схема ответа с данными записи истории
        Create: BookHistoryCreate - схема создания записи истории
        Update: BookHistoryUpdate - схема обновления записи истории
        Filter: BookHistoryFilter - схема фильтрации записей истории
    """

    async def get_by_book(self, book_id: UUID) -> List["Response"]:
        """Получает все записи истории изменений для указанной книги.

        :param book_id: Идентификатор книги
        :type book_id: UUID
        :return: Список записей истории изменений
        :rtype: List[BookHistoryInDB]
        """
        ...

    async def get_by_user(self, user_id: UUID) -> List["Response"]:
        """Получает все записи истории изменений, сделанных указанным пользователем.

        :param user_id: Идентификатор пользователя
        :type user_id: UUID
        :return: Список записей истории изменений
        :rtype: List[BookHistoryInDB]
        """
        ...


class BookHistoryCRUD(AbstractCRUD[Model, Create, Update, Filter, Response]):
    """Реализация CRUD операций для работы с историей изменений книг.

    Наследует базовые CRUD операции от AbstractCRUD и добавляет
    специализированные методы для работы с историей изменений:
    - Получение истории по книге
    - Получение истории по пользователю

    Все методы защищены декоратором @handle_db_errors для обработки ошибок БД.

    Типы:
        Model: BookHistory - SQLAlchemy модель записи истории
        Create: BookHistoryCreate - схема создания записи
        Update: BookHistoryUpdate - схема обновления записи
        Filter: BookHistoryFilter - схема фильтрации записей
        Response: BookHistoryInDB - схема ответа с данными записи

    Пример использования:
        # Инициализация
        history_crud = BookHistoryCRUD(db_session)

        # Создание записи истории
        new_entry = await history_crud.create(BookHistoryCreate(
            book_id=uuid.UUID("..."),
            user_id=uuid.UUID("..."),
            action="update",
            old_values={"title": "Old Title"},
            new_values={"title": "New Title"}
        ))

        # Получение истории книги
        book_history = await history_crud.get_by_book(book_id)

        # Получение истории пользователя
        user_history = await history_crud.get_by_user(user_id)
    """

    @property
    def model(self) -> type[Model]:
        """Возвращает класс SQLAlchemy модели BookHistory.

        Используется в базовых CRUD операциях для взаимодействия с БД.

        :return: Класс модели записи истории
        :rtype: type[BookHistory]
        """
        return Model

    @property
    def response_schema(self) -> type[Response]:
        """Возвращает Pydantic схему BookHistoryInDB для валидации ответов.

        Используется для преобразования объектов БД в Pydantic модели.

        :return: Класс схемы ответа
        :rtype: type[BookHistoryInDB]
        """
        return Response

    @handle_db_errors()
    async def get_by_book(self, book_id: UUID) -> list[Response]:
        """Получает полную историю изменений для конкретной книги.

        Возвращает все записи истории, связанные с указанной книгой,
        отсортированные по дате изменения (от новых к старым).

        :param book_id: Идентификатор книги
        :type book_id: UUID
        :return: Список записей истории изменений
        :rtype: list[BookHistoryInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        result = await self.db.execute(
            select(self.model).where(self.model.book_id == book_id)
        )
        return [self.response_schema.model_validate(h) for h in result.scalars()]

    @handle_db_errors()
    async def get_by_user(self, user_id: UUID) -> list[Response]:
        """Получает все изменения, сделанные конкретным пользователем.

        Возвращает все записи истории, где указанный пользователь
        был инициатором изменения, отсортированные по дате (от новых к старым).

        :param user_id: Идентификатор пользователя
        :type user_id: UUID
        :return: Список записей истории изменений
        :rtype: list[BookHistoryInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        result = await self.db.execute(
            select(self.model).where(self.model.user_id == user_id)
        )
        return [self.response_schema.model_validate(h) for h in result.scalars()]
