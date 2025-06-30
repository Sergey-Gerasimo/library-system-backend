from typing import Optional, Protocol
from abc import abstractmethod
from sqlalchemy import select, delete, update, and_

from services.abc import AbstractCRUD, ICRUD
from services.exceptions import handle_db_errors
from schemas import (
    UserBase,
    UserCreate as Create,
    UserFilter as Filter,
    UserInDB as Response,
    UserUpdate as Update,
)
from models import User as Model


class IUserCRUD(
    ICRUD["Response", "Create", "Update", "Filter"],
    Protocol,
):
    """Протокол для типизации CRUD операций с пользователями.

    Расширяет базовый интерфейс ICRUD специфичными методами для работы с пользователями.
    Определяет контракт, который должны реализовывать все CRUD сервисы для пользователей.

    Наследует:
        ICRUD: Базовый интерфейс CRUD операций

    Методы:
        get_by_username: Поиск пользователя по имени пользователя
        get_by_email: Поиск пользователя по email адресу

    Типы:
        Response: UserInDB - схема ответа с данными пользователя
        Create: UserCreate - схема создания пользователя
        Update: UserUpdate - схема обновления пользователя
        Filter: UserFilter - схема фильтрации пользователей
    """

    async def get_by_username(self, username: str) -> Optional[Response]:
        """Получает пользователя по уникальному имени пользователя.

        :param username: Имя пользователя для поиска
        :type username: str
        :return: Найденный пользователь или None
        :rtype: Optional[UserInDB]
        """
        ...

    async def get_by_email(self, email: str) -> Optional[Response]:
        """Получает пользователя по уникальному email адресу.

        :param email: Email адрес для поиска
        :type email: str
        :return: Найденный пользователь или None
        :rtype: Optional[UserInDB]
        """
        ...


class UserCRUD(AbstractCRUD[Model, Create, Update, Filter, Response]):
    """Конкретная реализация CRUD операций для работы с пользователями.

    Наследует базовые CRUD операции от AbstractCRUD и добавляет специфичные методы:
    - Поиск по имени пользователя
    - Поиск по email

    Все методы защищены декоратором @handle_db_errors для обработки ошибок БД.

    Типы:
        Model: User - SQLAlchemy модель пользователя
        Create: UserCreate - схема для создания пользователя
        Update: UserUpdate - схема для обновления пользователя
        Filter: UserFilter - схема для фильтрации пользователей
        Response: UserInDB - схема ответа с данными пользователя

    Пример использования:
        # Инициализация
        user_crud = UserCRUD(db_session)

        # Создание пользователя
        new_user = await user_crud.create(UserCreate(
            username="johndoe",
            email="john@example.com",
            password_hash="hashed_password"
        ))

        # Поиск по имени пользователя
        user = await user_crud.get_by_username("johndoe")

        # Поиск по email
        user = await user_crud.get_by_email("john@example.com")
    """

    @property
    def model(self) -> type[Model]:
        """Возвращает класс SQLAlchemy модели User.

        Используется в базовых CRUD операциях для взаимодействия с БД.

        :return: Класс модели пользователя
        :rtype: type[User]
        """

        return Model

    @property
    def response_schema(self) -> type[Response]:
        """Возвращает Pydantic схему UserInDB для валидации ответов.

        Используется для преобразования объектов БД в Pydantic модели.

        :return: Класс схемы ответа
        :rtype: type[UserInDB]
        """

        return Response

    @handle_db_errors()
    async def get_by_username(self, username: str) -> Optional[Response]:
        """Ищет пользователя по имени пользователя (username).

        Выполняет точный поиск по полю username (регистрозависимый).

        :param username: Имя пользователя для поиска
        :type username: str
        :return: Найденный пользователь или None
        :rtype: Optional[UserInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """

        result = await self.db.execute(
            select(self.model).where(self.model.username == username)
        )
        obj = result.scalar_one_or_none()
        return self.response_schema.model_validate(obj) if obj else None

    @handle_db_errors()
    async def get_by_email(self, email: str) -> Optional[Response]:
        """Ищет пользователя по email адресу.

        Выполняет точный поиск по полю email (регистрозависимый).

        :param email: Email адрес для поиска
        :type email: str
        :return: Найденный пользователь или None
        :rtype: Optional[UserInDB]
        :raises CRUDOperationError: При ошибках работы с БД
        """

        result = await self.db.execute(
            select(self.model).where(self.model.email == email)
        )
        obj = result.scalar_one_or_none()
        return self.response_schema.model_validate(obj) if obj else None
