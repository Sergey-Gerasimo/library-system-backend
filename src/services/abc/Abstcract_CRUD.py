from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy import select, delete, update, and_
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional, List, Any, Protocol, Dict
from sqlalchemy.ext.declarative import DeclarativeMeta
from datetime import date, datetime
from decimal import Decimal
from abc import ABC, abstractmethod

from services.exceptions import handle_db_errors


T = TypeVar("T")  # SQLAlchemy Model Type
C = TypeVar("C", bound=BaseModel)  # Create Schema Type
U = TypeVar("U", bound=BaseModel)  # Update Schema Type
F = TypeVar("F", bound=BaseModel)  # Filter Schema Type
R = TypeVar("R", bound=BaseModel)  # Response Schema Type


def sqlalchemy_to_dict(model: Any) -> Dict[str, Any]:
    """Преобразует SQLAlchemy модель в словарь с поддержкой специальных типов

    :param model: SQLAlchemy модель или список моделей
    :return: Словарь с данными модели
    :raises ValueError: Если передан объект не SQLAlchemy модели
    """

    result = {}
    for column in inspect(model).mapper.column_attrs:
        value = getattr(model, column.key)

        # Конвертация специальных типов
        if isinstance(value, (datetime, date)):
            result[column.key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[column.key] = float(value)
        elif hasattr(value, "__table__"):  # Для relationship полей
            result[column.key] = sqlalchemy_to_dict(value)
        else:
            result[column.key] = value

    return result


def validate_uuid(uuid_str):
    try:
        uuid_obj = UUID(uuid_str)
        return str(uuid_obj) == uuid_str  # Проверка точного соответствия
    except ValueError:
        return False


class ICRUD(Protocol, Generic[R, C, U, F]):
    """Базовый интерфейс для CRUD (Create, Read, Update, Delete) операций.

    Определяет стандартный контракт для всех CRUD-сервисов в системе.
    Использует дженерики для типизации схем данных.

    Типы:
        R: Схема ответа (Response)
        C: Схема создания (Create)
        U: Схема обновления (Update)
        F: Схема фильтрации (Filter)

    Методы:
        create: Создание новой записи
        get_by_id: Получение записи по ID
        update: Обновление записи
        delete: Удаление записи
        exists: Проверка существования записи
        get_all: Получение списка записей с пагинацией и фильтрацией

    """

    async def create(self, create_data: C) -> R:
        """Создает новую запись в базе данных.

        :param create_data: Данные для создания записи
        :type create_data: C
        :return: Созданная запись в формате response_schema
        :rtype: R
        """
        ...

    async def get_by_id(self, id: UUID) -> Optional[R]:
        """Получает запись по уникальному идентификатору.

        :param id: UUID записи
        :type id: UUID
        :return: Найденная запись или None
        :rtype: Optional[R]
        """
        ...

    async def update(self, id: UUID, update_data: U) -> Optional[R]:
        """Обновляет существующую запись.

        :param id: UUID обновляемой записи
        :type id: UUID
        :param update_data: Данные для обновления
        :type update_data: U
        :return: Обновленная запись или None если запись не найдена
        :rtype: Optional[R]
        """
        ...

    async def delete(self, id: UUID) -> bool:
        """Удаляет запись по идентификатору.

        :param id: UUID удаляемой записи
        :type id: UUID
        :return: True если запись удалена, False если не найдена
        :rtype: bool
        """
        ...

    async def exists(self, **kwargs) -> bool:
        """Проверяет существование записи по указанным критериям.

        :param kwargs: Параметры фильтрации (например, email="user@example.com")
        :return: True если запись существует, иначе False
        :rtype: bool
        """
        ...

    async def get_all(
        self,
        filter: Optional[F] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
    ) -> List[R]:
        """Получает список записей с возможностью фильтрации и пагинации.

        :param filter: Параметры фильтрации, defaults to None
        :type filter: Optional[F]
        :param limit: Максимальное количество записей, defaults to 100
        :type limit: int
        :param offset: Смещение выборки, defaults to 0
        :type offset: int
        :param order_by: Поле для сортировки (например, "created_at.desc()"), defaults to None
        :type order_by: Optional[str]
        :return: Список записей
        :rtype: List[R]
        """
        ...


class AbstractCRUD(ABC, Generic[T, C, U, F, R]):
    """Абстрактный базовый класс для CRUD операций с автоматической обработкой ошибок.

    Предоставляет готовую реализацию стандартных операций Create, Read, Update, Delete
    для работы с SQLAlchemy моделями и Pydantic схемами. Все методы защищены декоратором
    @handle_db_errors для автоматического управления транзакциями.

    Типы:
        T: SQLAlchemy модель (должна содержать поле id типа UUID)
        C: Pydantic схема для создания записи (Create)
        U: Pydantic схема для обновления записи (Update)
        F: Pydantic схема для фильтрации записей (Filter)
        R: Pydantic схема для ответа API (Response)

    Пример использования:
        class ProductCRUD(AbstractCRUD[Product, ProductCreate, ProductUpdate, ProductFilter, ProductResponse]):
            @property
            def model(self) -> type[Product]:
                return Product

            @property
            def response_schema(self) -> type[ProductResponse]:
                return ProductResponse

    Особенности:
        - Автоматический rollback при ошибках
        - Валидация данных через Pydantic
        - Поддержка пагинации и фильтрации
        - Оптимизированные запросы к БД
    """

    def __init__(self, db_session: AsyncSession):
        """Инициализирует CRUD сервис с подключением к базе данных.

        :param db_session: Асинхронная сессия SQLAlchemy
        :type db_session: AsyncSession
        :raises TypeError: Если передан не AsyncSession
        """
        if not isinstance(db_session, AsyncSession):
            raise TypeError("db_session must be AsyncSession")

        self.db = db_session

    @property
    @abstractmethod
    def model(self) -> type[T]:
        """Возвращает класс SQLAlchemy модели для операций CRUD.

        :return: Класс SQLAlchemy модели
        :rtype: type[T]
        """
        pass

    @property
    @abstractmethod
    def response_schema(self) -> type[R]:
        """Возвращает Pydantic схему для преобразования результатов.

        :return: Класс Pydantic схемы ответа
        :rtype: type[R]
        """
        pass

    @handle_db_errors()
    async def create(self, create_data: C) -> R:
        """Создает новую запись в базе данных.

        :param create_data: Данные для создания записи
        :type create_data: C
        :return: Созданная запись в формате response_schema
        :rtype: R
        :raises CRUDIntegrityError: При нарушении ограничений БД
        :raises CRUDOperationError: При других ошибках работы с БД
        """
        obj = self.model(**create_data.model_dump())
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return self.response_schema.model_validate(sqlalchemy_to_dict(obj))

    @handle_db_errors()
    async def get_by_id(self, id: UUID) -> Optional[R]:
        """Получает запись по UUID идентификатору.

        :param id: Уникальный идентификатор записи
        :type id: UUID
        :return: Найденная запись или None
        :rtype: Optional[R]
        :raises CRUDOperationError: При других ошибках работы с БД
        """

        result = await self.db.execute(select(self.model).where(self.model.id == id))
        obj = result.scalar_one_or_none()
        return (
            self.response_schema.model_validate(sqlalchemy_to_dict(obj))
            if obj
            else None
        )

    @handle_db_errors()
    async def get_all(
        self,
        filter: Optional[F] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
    ) -> List[R]:
        """Получает список записей с пагинацией и фильтрацией.

        :param filter: Параметры фильтрации, defaults to None
        :type filter: Optional[F]
        :param limit: Максимальное количество записей, defaults to 100
        :type limit: int
        :param offset: Смещение выборки, defaults to 0
        :type offset: int
        :param order_by: Поле для сортировки (например, "created_at.desc()"), defaults to None
        :type order_by: Optional[str]
        :return: Список записей в формате response_schema
        :rtype: List[R]
        :raises CRUDOperationError: При ошибках работы с БД
        """
        query = select(self.model)

        if filter:
            conditions = self._build_filter_conditions(filter)
            if conditions:
                query = query.where(and_(*conditions))

        if order_by:
            query = query.order_by(order_by)

        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        items = result.scalars().all()
        return [
            self.response_schema.model_validate(sqlalchemy_to_dict(obj))
            for obj in items
        ]

    @handle_db_errors()
    async def update(self, id: UUID, update_data: U) -> Optional[R]:
        """Обновляет существующую запись частично (PATCH-семантика).

        :param id: UUID обновляемой записи
        :type id: UUID
        :param update_data: Данные для обновления (только изменяемые поля)
        :type update_data: U
        :return: Обновленная запись или None если запись не найдена
        :rtype: Optional[R]
        :raises CRUDIntegrityError: При нарушении ограничений БД
        :raises CRUDOperationError: При других ошибках работы с БД
        """
        obj = await self.db.get(self.model, id)
        if not obj:
            return None

        update_values = update_data.model_dump(exclude_unset=True)
        await self.db.execute(
            update(self.model).where(self.model.id == id).values(**update_values)
        )
        await self.db.commit()
        await self.db.refresh(obj)
        return self.response_schema.model_validate(sqlalchemy_to_dict(obj))

    @handle_db_errors()
    async def delete(self, id: UUID) -> bool:
        """Удаляет запись по идентификатору.

        :param id: UUID удаляемой записи
        :type id: UUID
        :return: True если запись удалена, False если не найдена
        :rtype: bool
        :raises CRUDOperationError: При ошибках работы с БД
        """
        obj = await self.db.get(self.model, id)
        if not obj:
            return False

        await self.db.execute(delete(self.model).where(self.model.id == id))
        await self.db.commit()
        return True

    def _build_filter_conditions(self, filter: F) -> List[Any]:
        """Строит условия фильтрации для SQL запроса на основе схемы.

        :param filter: Схема фильтрации
        :type filter: F
        :return: Список условий для SQLAlchemy where()
        :rtype: List[Any]
        """
        conditions = []
        for field, value in filter.model_dump(exclude_unset=True).items():
            if value is not None:
                if isinstance(value, str):
                    conditions.append(getattr(self.model, field).ilike(f"%{value}%"))
                else:
                    conditions.append(getattr(self.model, field) == value)
        return conditions

    @handle_db_errors()
    async def exists(self, **kwargs) -> bool:
        """Проверяет существование записи по указанным критериям.

        :param kwargs: Параметры фильтрации (например, email="user@example.com")
        :return: True если запись существует, иначе False
        :rtype: bool
        :raises CRUDOperationError: При ошибках работы с БД
        """
        query = select(self.model).filter_by(**kwargs)
        result = await self.db.execute(query.exists())
        return result.scalar_one()
