from abc import ABC, abstractmethod
from uuid import UUID
from functools import wraps
from typing import Callable, TypeVar, Generic, Type, Optional, List, Any
from pydantic import BaseModel
from loguru import logger

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
            logger.error("Invalid CRUD layer provided", crud_type=type(crud).__name__)
            raise ServiceError("Invalid CRUD layer provided")

        self._crud = crud
        self._logger = logger.bind(service=self.__class__.__name__)

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
        log_context = {"operation": "create", "schema_type": type(schema).__name__}

        self._logger.debug("Creating record", **log_context)

        try:
            result = await self._crud.create(schema)
            self._logger.success(
                "Record created", **log_context, record_id=getattr(result, "id", None)
            )
            return result

        except CRUDIntegrityError as e:
            self._logger.error(
                "Integrity error on create",
                **log_context,
                error=str(e),
                error_type="integrity",
            )
            raise ServiceIntegrityError(f"Create failed: {str(e)}") from e

        except Exception as e:
            self._logger.error(
                "Create operation failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceError(f"Create failed: {str(e)}") from e

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

        log_context = {"operation": "get", "record_id": str(id)}
        self._logger.debug("Fetching record", **log_context)

        try:
            result = await self._crud.get_by_id(id)

            if result is None:
                self._logger.warning("Record not found", **log_context)
                raise ServiceNotFoundError(f"Record {id} not found")

            self._logger.debug("Record found", **log_context)

            return result

        except CRUDNotFoundError as e:
            self._logger.warning("Record not found (CRUD)", **log_context, error=str(e))
            raise ServiceNotFoundError(str(e)) from e

        except Exception as e:
            self._logger.error(
                "Get operation failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceError(f"Get failed: {str(e)}") from e

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

        log_context = {
            "operation": "update",
            "record_id": str(id),
            "schema_type": type(schema).__name__,
        }

        self._logger.info("Updating record", **log_context)

        try:
            result = await self._crud.update(id, schema)
            if result is None:
                self._logger.warning("Record not found for update", **log_context)
                raise ServiceNotFoundError(f"Record {id} not found")

            self._logger.success("Record updated", **log_context)
            return result

        except CRUDNotFoundError as e:
            self._logger.warning("Record not found (CRUD)", **log_context, error=str(e))
            raise ServiceNotFoundError(str(e)) from e
        except CRUDIntegrityError as e:
            self._logger.error(
                "Integrity error on update",
                **log_context,
                error=str(e),
                error_type="integrity",
            )
            raise ServiceIntegrityError(f"Update failed: {str(e)}") from e
        except Exception as e:
            self._logger.error(
                "Update operation failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceError(f"Update failed: {str(e)}") from e

    async def delete(self, id: UUID) -> bool:
        """Удаление записи с обработкой ошибок.

        :param id: Идентификатор записи
        :type id: UUID
        :return: Статус успешности удаления
        :rtype: bool
        :raises ServiceNotFoundError: Если запись не найдена
        :raises ServiceError: При других ошибках операции
        """
        log_context = {"operation": "delete", "record_id": str(id)}

        self._logger.warning("Deleting record", **log_context)

        try:
            result = await self._crud.delete(id)
            if not result:
                self._logger.warning("Record not found for deletion", **log_context)
                raise ServiceNotFoundError(f"Record {id} not found")

            self._logger.success("Record deleted", **log_context)
            return True

        except CRUDNotFoundError as e:
            self._logger.warning("Record not found (CRUD)", **log_context, error=str(e))
            raise ServiceNotFoundError(str(e)) from e

        except Exception as e:
            self._logger.error(
                "Delete operation failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceError(f"Delete failed: {str(e)}") from e

    @handle_service_errors()
    async def exists(self, **kwargs) -> bool:
        """Проверка существования записи по критериям.

        :param kwargs: Параметры фильтрации
        :return: Флаг существования
        :rtype: bool
        :raises ServiceError: При ошибках операции
        """

        log_context = {"operation": "exists", "filters": kwargs}

        self._logger.debug("Checking record existence", **log_context)

        try:
            exists = await self._crud.exists(**kwargs)
            self._logger.debug("Existence check result", **log_context, exists=exists)
            return exists
        except Exception as e:
            self._logger.error(
                "Existence check failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceError(f"Exists check failed: {str(e)}") from e

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

        log_context = {
            "operation": "get_all",
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
            "has_filter": filter is not None,
        }

        self._logger.debug("Fetching records list", **log_context)

        if limit > 1000:
            self._logger.error("Limit too large", **log_context, max_allowed=1000)
            raise ServiceValidationError("Максимальный лимит - 1000 записей")

        if offset < 0:
            self._logger.error("Invalid offset", **log_context)
            raise ServiceValidationError("Смещение не может быть отрицательным")

        try:
            results = await self._crud.get_all(
                filter=filter, limit=limit, offset=offset, order_by=order_by
            )
            self._logger.debug("Records fetched", **log_context, count=len(results))
            return results

        except Exception as e:
            self._logger.error(
                "Get all operation failed",
                **log_context,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ServiceError(f"Get all failed: {str(e)}") from e
