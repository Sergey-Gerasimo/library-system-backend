from services.exceptions.crud_exceptions import (
    CRUDConnectionError,
    CRUDIntegrityError,
    CRUDMultipleResultsError,
    CRUDNotFoundError,
    CRUDOperationError,
    CRUDRetryableError,
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
