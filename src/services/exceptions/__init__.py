from .crud_exceptions import (
    handle_db_errors,
    CRUDOperationError,
    CRUDNotFoundError,
    CRUDMultipleResultsError,
    CRUDIntegrityError,
    CRUDConnectionError,
    CRUDRetryableError,
)

from .service_exceptions import (
    ServiceError,
    ServiceIntegrityError,
    ServiceNotFoundError,
    ServiceOperationError,
    ServiceTemporaryError,
    ServiceValidationError,
    handle_service_errors,
    handle_storage_service_errors,
)

from .storage_exeptions import (
    StorageOperationError,
    StorageAccessDeniedError,
    StorageConnectionError,
    StorageInternalError,
    StorageInvalidStateError,
    StorageNotFoundError,
    handle_storage_errors,
)

__all__ = [
    # Декораторы
    "handle_db_errors",
    "handle_service_errors",
    "handle_storage_errors",
    "handle_storage_service_errors",
    # Ошибки CRUD
    "CRUDOperationError",
    "CRUDNotFoundError",
    "CRUDMultipleResultsError",
    "CRUDIntegrityError",
    "CRUDConnectionError",
    "CRUDRetryableError",
    # ошибки сервиса
    "ServiceError",
    "ServiceIntegrityError",
    "ServiceNotFoundError",
    "ServiceOperationError",
    "ServiceTemporaryError",
    "ServiceValidationError",
    # ошибки Storage
    "StorageOperationError",
    "StorageAccessDeniedError",
    "StorageConnectionError",
    "StorageInternalError",
    "StorageInvalidStateError",
    "StorageNotFoundError",
]
