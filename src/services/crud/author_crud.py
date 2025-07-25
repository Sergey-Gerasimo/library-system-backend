from typing import Optional, Protocol
from sqlalchemy import select, delete, update, and_
from abc import abstractmethod

from services.abc import AbstractCRUD, ICRUD
from services.exceptions import handle_db_errors
from models import Author as Model
from schemas import (
    AuthorCreate as Create,
    AuthorInDB as Response,
    AuthorUpdate as Update,
    AuthorFilter as Filter,
)


class IAuthorCRUD(
    ICRUD["Response", "Create", "Update", "Filter"],
    Protocol,
):
    """Протокол для типизации CRUD операций с авторами.

    Расширяет базовый интерфейс ICRUD специфичными методами для работы
    с авторами. Определяет контракт для всех реализаций сервиса авторов.

    Методы:
        get_by_name: Поиск автора по точному имени
        search_in_bio: Поиск авторов по ключевым словам в биографии

    Типы:
        Response: AuthorInDB - схема ответа с данными автора
        Create: AuthorCreate - схема создания автора
        Update: AuthorUpdate - схема обновления автора
        Filter: AuthorFilter - схема фильтрации авторов
    """

    async def get_by_name(self, name: str) -> Optional[Response]:
        """Находит автора по полному совпадению имени.

        :param name: Полное имя автора для поиска
        :type name: str
        :return: Найденный автор или None
        :rtype: Optional[AuthorInDB]
        """
        ...

    async def search_in_bio(self, search_term: str) -> list[Response]:
        """Ищет авторов по вхождению строки в биографию.

        :param search_term: Строка для поиска в биографии
        :type search_term: str
        :return: Список авторов с совпадениями
        :rtype: List[AuthorInDB]
        """
        ...


class AuthorCRUD(AbstractCRUD[Model, Create, Update, Filter, Response]):
    """Реализация CRUD операций для работы с авторами.

    Наследует базовые CRUD операции от AbstractCRUD и добавляет
    специализированные методы для работы с авторами:
    - Поиск по точному имени
    - Поиск по биографии

    Все методы защищены декоратором @handle_db_errors для обработки ошибок БД.

    Типы:
        Model: Author - SQLAlchemy модель автора
        Create: AuthorCreate - схема создания автора
        Update: AuthorUpdate - схема обновления автора
        Filter: AuthorFilter - схема фильтрации авторов
        Response: AuthorInDB - схема ответа с данными автора

    Пример использования:
        # Инициализация
        author_crud = AuthorCRUD(db_session)

        # Создание автора
        new_author = await author_crud.create(AuthorCreate(
            name="Фёдор Достоевский",
            bio="Русский писатель, мыслитель, философ",
            birth_date="1821-11-11"
        ))

        # Поиск по имени
        author = await author_crud.get_by_name("Фёдор Достоевский")

        # Поиск по биографии
        philosophers = await author_crud.search_in_bio("философ")
    """

    @property
    def model(self) -> type[Model]:
        """Возвращает класс SQLAlchemy модели Author.

        Используется в базовых CRUD операциях для взаимодействия с БД.

        :return: Класс модели автора
        :rtype: type[Author]
        """
        return Model

    @property
    def response_schema(self) -> type[Response]:
        """Возвращает Pydantic схему AuthorInDB для валидации ответов.

        Используется для преобразования объектов БД в Pydantic модели.

        :return: Класс схемы ответа
        :rtype: type[AuthorInDB]
        """
        return Response

    @handle_db_errors()
    async def get_by_name(self, name: str) -> Optional[Response]:
        """Находит автора по полному совпадению имени.

        Поиск выполняется по точному регистрозависимому совпадению.
        Для поиска по части имени используйте метод get_all с фильтром.

        :param name: Полное имя автора
        :type name: str
        :return: Найденный автор или None
        :rtype: Optional[AuthorInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        result = await self.db.execute(
            select(self.model).where(self.model.name == name)
        )
        author = result.scalar_one_or_none()
        return self.response_schema.model_validate(author) if author else None

    @handle_db_errors()
    async def search_in_bio(self, search_term: str) -> list[Response]:
        """Ищет авторов по вхождению строки в биографию.

        Поиск выполняется без учета регистра (ilike). Возвращает всех авторов,
        в биографии которых содержится указанная подстрока.

        :param search_term: Строка для поиска в биографии
        :type search_term: str
        :return: Список авторов с совпадениями
        :rtype: list[AuthorInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        result = await self.db.execute(
            select(self.model).where(self.model.bio.ilike(f"%{search_term}%"))
        )
        return [self.response_schema.model_validate(a) for a in result.scalars().all()]
