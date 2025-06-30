from abc import ABC, abstractmethod
from uuid import UUID
from functools import wraps
from typing import Callable, TypeVar, Generic, Type, Optional, List, Any
from pydantic import BaseModel

from services.abc.Abstcract_CRUD import AbstractCRUD
from services.exceptions import (
    CRUDConnectionError,
    CRUDIntegrityError,
    CRUDMultipleResultsError,
    CRUDNotFoundError,
    CRUDOperationError,
    CRUDRetryableError,
    ServiceValidationError,
    ServiceError,
    ServiceIntegrityError,
    ServiceNotFoundError,
    ServiceOperationError,
    ServiceTemporaryError,
    handle_service_errors,
)

CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
FilterSchema = TypeVar("FilterSchema", bound=BaseModel)
ResponseSchema = TypeVar("ResponseSchema", bound=BaseModel)

ModelType = TypeVar("ModelType")

CRUD = TypeVar(
    "CRUD",
    bound=AbstractCRUD[
        ModelType, CreateSchema, UpdateSchema, FilterSchema, ResponseSchema
    ],
)


class AbstractService(
    ABC, Generic[ModelType, CreateSchema, UpdateSchema, FilterSchema, ResponseSchema]
):
    """Абстрактный базовый сервис для бизнес-логики.

    Предоставляет стандартные CRUD операции поверх абстрактного репозитория,
    добавляя обработку бизнес-правил и преобразование ошибок.

    Типы:
        ModelType: SQLAlchemy модель
        CreateSchema: Pydantic схема для создания
        UpdateSchema: Pydantic схема для обновления
        FilterSchema: Pydantic схема для фильтрации
        ResponseSchema: Pydantic схема ответа

    Наследует:
        ABC: Абстрактный базовый класс
        Generic: Для параметризации типов

    Пример использования:
        class UserService(AbstractService[User, UserCreate, UserUpdate, UserFilter, UserResponse]):
            pass
    """

    def __init__(self, crud: CRUD):
        """Инициализация сервиса с CRUD слоем.

        :param crud: CRUD слой для работы с данными
        :type crud: AbstractCRUD
        :raises ServiceError: Если передан некорректный CRUD слой
        """
        if not isinstance(crud, AbstractCRUD):
            raise ServiceError("Invalid CRUD layer provided")
        self._crud = crud

    @property
    def crud(self) -> CRUD:
        """Доступ к CRUD слою.

        :return: Экземпляр CRUD
        :rtype: AbstractCRUD
        """
        return self._crud

    @handle_service_errors()
    async def create(self, schema: CreateSchema) -> ResponseSchema:
        """Создание новой записи с валидацией и обработкой ошибок.

        :param schema: Данные для создания
        :type schema: CreateSchema
        :return: Созданная запись
        :rtype: ResponseSchema
        :raises ServiceValidationError: При ошибках валидации данных
        :raises ServiceIntegrityError: При нарушении целостности данных
        :raises ServiceError: При других ошибках операции
        """

        try:
            return await self._crud.create(schema)
        except CRUDIntegrityError as e:
            raise ServiceIntegrityError(f"Create failed: {str(e)}") from e

    @handle_service_errors()
    async def get(self, id: UUID) -> ResponseSchema:
        """Получение записи по ID с обработкой ошибок.

        :param id: Идентификатор записи
        :type id: UUID
        :return: Найденная запись
        :rtype: ResponseSchema
        :raises ServiceNotFoundError: Если запись не найдена
        :raises ServiceError: При других ошибках операции
        """

        try:
            result = await self._crud.get_by_id(id)
            if result is None:
                raise ServiceNotFoundError(f"Record {id} not found")
            return result
        except CRUDNotFoundError as e:
            raise ServiceNotFoundError(str(e)) from e

    @handle_service_errors(max_retries=3)
    async def update(self, id: UUID, schema: UpdateSchema) -> ResponseSchema:
        """Обновление записи с валидацией и повторными попытками.

        :param id: Идентификатор записи
        :type id: UUID
        :param schema: Данные для обновления
        :type schema: UpdateSchema
        :return: Обновленная запись
        :rtype: ResponseSchema
        :raises ServiceNotFoundError: Если запись не найдена
        :raises ServiceIntegrityError: При нарушении целостности
        :raises ServiceError: При других ошибках операции
        """
        try:
            result = await self._crud.update(id, schema)
            if result is None:
                raise ServiceNotFoundError(f"Record {id} not found")
            return result
        except CRUDNotFoundError as e:
            raise ServiceNotFoundError(str(e)) from e
        except CRUDIntegrityError as e:
            raise ServiceIntegrityError(f"Update failed: {str(e)}") from e

    async def delete(self, id: UUID) -> bool:
        """Удаление записи с обработкой ошибок.

        :param id: Идентификатор записи
        :type id: UUID
        :return: Статус успешности удаления
        :rtype: bool
        :raises ServiceNotFoundError: Если запись не найдена
        :raises ServiceError: При других ошибках операции
        """
        try:
            if not await self._crud.delete(id):
                raise ServiceNotFoundError(f"Record {id} not found")
            return True

        except CRUDNotFoundError as e:
            raise ServiceNotFoundError(str(e)) from e

    @handle_service_errors()
    async def exists(self, **kwargs) -> bool:
        """Проверка существования записи по критериям.

        :param kwargs: Параметры фильтрации
        :return: Флаг существования
        :rtype: bool
        :raises ServiceError: При ошибках операции
        """
        return await self._crud.exists(**kwargs)

    @handle_service_errors()
    async def get_all(
        self,
        filter: Optional[FilterSchema] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
    ) -> List[ResponseSchema]:
        """Получение списка записей с пагинацией и фильтрацией.

        :param filter: Параметры фильтрации, defaults to None
        :type filter: Optional[FilterSchema]
        :param limit: Лимит записей, defaults to 100
        :type limit: int
        :param offset: Смещение, defaults to 0
        :type offset: int
        :param order_by: Поле сортировки, defaults to None
        :type order_by: Optional[str]
        :return: Список записей
        :rtype: List[ResponseSchema]
        :raises ServiceValidationError: При невалидных параметрах
        :raises ServiceError: При ошибках операции
        """

        if limit > 1000:
            raise ServiceValidationError("Максимальный лимит - 1000 записей")

        if offset < 0:
            raise ServiceValidationError("Смещение не может быть отрицательным")

        return await self._crud.get_all(
            filter=filter, limit=limit, offset=offset, order_by=order_by
        )
