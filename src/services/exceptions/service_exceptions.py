from services.exceptions.crud_exceptions import (
    CRUDConnectionError,
    CRUDIntegrityError,
    CRUDMultipleResultsError,
    CRUDNotFoundError,
    CRUDOperationError,
    CRUDRetryableError,
)
from services.exceptions.storage_exeptions import (
    StorageAccessDeniedError,
    StorageConnectionError,
    StorageInternalError,
    StorageInvalidStateError,
    StorageNotFoundError,
    StorageOperationError,
)

from functools import wraps
from typing import Callable, TypeVar, Any, Coroutine, ParamSpec
import asyncio


class ServiceError(Exception):
    """Базовое исключение для всех ошибок сервисного слоя"""

    pass


class ServiceNotFoundError(ServiceError):
    """Ошибка при отсутствии запрашиваемых данных"""

    pass


class ServiceValidationError(ServiceError):
    """Ошибка валидации входных данных"""

    pass


class ServiceIntegrityError(ServiceError):
    """Ошибка целостности данных при операциях"""

    pass


class ServiceOperationError(ServiceError):
    """Ошибка выполнения операции в сервисе"""

    pass


class ServiceTemporaryError(ServiceError):
    """Временная ошибка сервиса (можно повторить)"""

    pass


P = ParamSpec("P")  # Параметры оригинальной функции
R = TypeVar("R")  # Возвращаемый тип


def handle_storage_service_errors(
    max_retries: int = 1, retry_delay: float = 0.1
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]
]:
    """Декоратор для обработки и трансформации ошибок хранилища в сервисном слое.

    Обеспечивает:
    - Преобразование ошибок хранилища в стандартные сервисные исключения
    - Автоматические повторные попытки для временных ошибок подключения
    - Единообразную обработку ошибок на уровне сервиса
    - Сохранение цепочки исключений (exception chaining)

    Args:
        max_retries: Максимальное количество повторных попыток при временных ошибках
                    (default: 1)
        retry_delay: Базовая задержка между попытками в секундах (default: 0.1)
                    Реальная задержка рассчитывается как retry_delay * attempt_number

    Returns:
        Декорированную асинхронную функцию с обработкой ошибок хранилища

    Raises:
        ServiceNotFoundError: При отсутствии запрашиваемых данных в хранилище
        ServiceValidationError: При ошибках доступа/авторизации
        ServiceIntegrityError: При недопустимом состоянии данных
        ServiceTemporaryError: Для временных проблем с подключением к хранилищу
        ServiceOperationError: Для прочих ошибок операций с хранилищем

    Пример использования:
        @handle_storage_service_errors(max_retries=2)
        async def fetch_user_data(user_id: UUID) -> UserData:
            ...
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except StorageNotFoundError as e:
                raise ServiceNotFoundError(str(e)) from e

            except StorageAccessDeniedError as e:
                raise ServiceValidationError(str(e)) from e

            except StorageInvalidStateError as e:
                raise ServiceIntegrityError(str(e)) from e

            except (StorageInternalError, StorageOperationError) as e:
                raise ServiceOperationError(str(e)) from e

            except StorageConnectionError as e:
                raise ServiceTemporaryError(str(e)) from e

            except Exception as e:
                raise ServiceOperationError(f"Неизвестная ошибка: {str(e)}") from e

        return wrapper

    return decorator


def handle_service_errors(
    max_retries: int = 1, retry_delay: float = 0.1
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]
]:
    """Декоратор для обработки и трансформации ошибок в сервисном слое.

    Обеспечивает:
    - Преобразование CRUD исключений в сервисные исключения
    - Повторные попытки для временных ошибок
    - Единообразную обработку ошибок
    - Логирование ошибок (должно быть добавлено в реализацию)

    Args:
        max_retries: Максимальное количество повторных попыток (default: 1)
        retry_delay: Базовая задержка между попытками в секундах (default: 0.1)

    Returns:
        Декорированную асинхронную функцию с обработкой ошибок

    Raises:
        ServiceNotFoundError: При отсутствии запрашиваемых данных
        ServiceValidationError: При ошибках валидации
        ServiceIntegrityError: При нарушениях целостности данных
        ServiceTemporaryError: Для временных/повторяемых ошибок
        ServiceOperationError: При ошибках выполнения операций
        ServiceError: Базовое исключение для прочих ошибок

    Пример использования:
        @handle_service_errors(max_retries=3)
        async def get_user_profile(user_id: UUID) -> UserProfile:
            ...
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except CRUDNotFoundError as e:
                    raise ServiceNotFoundError(str(e)) from e

                except CRUDIntegrityError as e:
                    raise ServiceIntegrityError(str(e)) from e

                except (CRUDConnectionError, CRUDRetryableError) as e:
                    last_error = e
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue

                    raise ServiceTemporaryError(str(e)) from e

                except CRUDOperationError as e:
                    raise ServiceOperationError(str(e)) from e

                except Exception as e:
                    raise ServiceError("Internal service error") from e

            raise last_error if last_error else ServiceError("Unknown service error")

        return wrapper

    return decorator
