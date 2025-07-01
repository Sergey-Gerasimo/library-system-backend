from functools import wraps
from typing import Callable, Coroutine, TypeVar, Any, ParamSpec
import asyncio
from aiobotocore.client import AioBaseClient
from botocore.exceptions import ClientError

P = ParamSpec("P")
R = TypeVar("R")


class StorageOperationError(Exception):
    """Базовое исключение для ошибок операций с Storage"""

    pass


class StorageNotFoundError(StorageOperationError):
    """Ошибка при отсутствии запрашиваемого файла или бакета"""

    pass


class StorageAccessDeniedError(StorageOperationError):
    """Ошибка доступа к Storage ресурсу"""

    pass


class StorageConnectionError(StorageOperationError):
    """Ошибка подключения к Storage"""

    pass


class StorageInvalidStateError(StorageOperationError):
    """Ошибка состояния объекта (например, объект в Glacier)"""

    pass


class StorageInternalError(StorageOperationError):
    """Внутренняя ошибка Storage"""

    pass


def handle_storage_errors(
    max_retries: int = 3, retry_delay: float = 0.5
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]
]:
    """Декоратор для обработки ошибок при работе с Storage.

    Преобразует ошибки aiobotocore в собственные исключения сервиса.
    Поддерживает повторные попытки для сетевых ошибок.

    Args:
        max_retries: Максимальное количество попыток для сетевых ошибок
        retry_delay: Задержка между попытками в секундах

    Raises:
        StorageNotFoundError: Когда файл или бакет не найдены
        StorageAccessDeniedError: При проблемах с авторизацией
        StorageInvalidStateError: При проблемах с состоянием объекта
        StorageInternalError: При внутренних ошибках Storage
        StorageConnectionError: При проблемах с подключением
        StorageOperationError: Базовое исключение для других ошибок
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code")
                    error_message = e.response.get("Error", {}).get("Message", str(e))

                    if error_code == "NoSuchKey" or error_code == "NoSuchBucket":
                        raise StorageNotFoundError(
                            f"Ресурс не найден: {error_message}"
                        ) from e
                    elif error_code == "AccessDenied":
                        raise StorageAccessDeniedError(
                            f"Доступ запрещен: {error_message}"
                        ) from e
                    elif error_code == "InvalidObjectState":
                        raise StorageInvalidStateError(
                            f"Неверное состояние объекта: {error_message}"
                        ) from e
                    elif error_code == "InternalError":
                        raise StorageInternalError(
                            f"Внутренняя ошибка Storage: {error_message}"
                        ) from e
                    else:
                        raise StorageOperationError(
                            f"Ошибка Storage: {error_message}"
                        ) from e

                except FileNotFoundError as e:
                    raise StorageNotFoundError(str(e)) from e

                except (ConnectionError, TimeoutError) as e:
                    last_error = e
                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    raise StorageConnectionError(f"Ошибка подключения: {str(e)}") from e

                except Exception as e:
                    raise StorageOperationError(
                        f"Непредвиденная ошибка: {str(e)}"
                    ) from e

            raise StorageConnectionError(
                f"Превышено количество попыток. Последняя ошибка: {str(last_error)}"
            ) from last_error

        return wrapper

    return decorator
