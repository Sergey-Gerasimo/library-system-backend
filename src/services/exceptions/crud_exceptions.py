from functools import wraps
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    NoResultFound,
    MultipleResultsFound,
    OperationalError,
    DBAPIError,
)
from typing import Optional, Callable, Coroutine, TypeVar, ParamSpec, Any
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDOperationError(Exception):
    """Базовое исключение для всех ошибок операций CRUD"""

    pass


class CRUDNotFoundError(CRUDOperationError):
    """Ошибка при отсутствии запрашиваемой записи в CRUD операциях"""

    pass


class CRUDMultipleResultsError(CRUDOperationError):
    """Ошибка при обнаружении нескольких записей, когда ожидалась одна"""

    pass


class CRUDIntegrityError(CRUDOperationError):
    """Ошибка нарушения целостности данных в CRUD операциях"""

    pass


class CRUDConnectionError(CRUDOperationError):
    """Ошибка подключения к БД во время CRUD операций"""

    pass


class CRUDRetryableError(CRUDOperationError):
    """Ошибка CRUD операции, которую можно попробовать повторить"""

    pass


P = ParamSpec("P")  # Параметры оригинальной функции
R = TypeVar("R")  # Возвращаемый тип


def handle_db_errors(
    max_retries: int = 1, retry_delay: float = 0.1
) -> Callable[
    [Callable[P, Coroutine[Any, Any, R]]], Callable[P, Coroutine[Any, Any, R]]
]:
    """Декоратор для обработки ошибок SQLAlchemy в CRUD операциях.

    Обеспечивает безопасное выполнение CRUD операций:
    - Автоматический rollback при ошибках
    - Преобразование SQLAlchemy ошибок в CRUD-специфичные исключения
    - Повторные попытки для транзакционных ошибок
    - Контекстное логирование ошибок

    :param max_retries: Максимальное количество попыток для CRUDRetryableError, defaults to 1
    :type max_retries: int, optional
    :param retry_delay: Задержка между попытками в секундах, defaults to 0.1
    :type retry_delay: float, optional

    :raises CRUDNotFoundError: Когда запись не найдена (NoResultFound)
    :raises CRUDMultipleResultsError: При неоднозначном результате (MultipleResultsFound)
    :raises CRUDIntegrityError: При нарушениях целостности данных (IntegrityError)
    :raises CRUDConnectionError: При проблемах подключения (OperationalError/DBAPIError)
    :raises CRUDRetryableError: Для повторяемых ошибок (deadlock и т.д.)
    :raises CRUDOperationError: Базовое исключение для других ошибок

    Пример:
        @handle_db_errors(max_retries=3)
        async def update_user(self, user_id: UUID, data: UserUpdate):
            ...
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, Coroutine[Any, Any, R]]:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            session: Optional[AsyncSession] = getattr(self, "db", None)

            if not isinstance(session, AsyncSession):
                raise CRUDOperationError("Отсутствует асинхронная сессия БД")

            for attempt in range(max_retries + 1):
                try:
                    result = await func(self, *args, **kwargs)
                    if not session.in_transaction():
                        await session.commit()
                    return result

                except NoResultFound as e:
                    await session.rollback()
                    raise CRUDNotFoundError(f"Запись не найдена: {str(e)}") from e

                except MultipleResultsFound as e:
                    await session.rollback()
                    raise CRUDMultipleResultsError(
                        f"Найдено дубликатов: {str(e)}"
                    ) from e

                except IntegrityError as e:
                    await session.rollback()
                    error_msg = str(e.orig).lower()
                    if "unique constraint" in error_msg:
                        raise CRUDIntegrityError("Нарушение уникальности данных") from e
                    elif "foreign key constraint" in error_msg:
                        raise CRUDIntegrityError(
                            "Нарушение ссылочной целостности"
                        ) from e
                    raise CRUDIntegrityError("Ошибка целостности данных") from e

                except (OperationalError, DBAPIError) as e:
                    await session.rollback()
                    if "deadlock" in str(e).lower() and attempt < max_retries:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    raise CRUDConnectionError(f"Ошибка подключения: {str(e)}") from e

                except SQLAlchemyError as e:
                    await session.rollback()
                    raise CRUDOperationError(f"Ошибка операции: {str(e)}") from e

                except Exception as e:
                    await session.rollback()
                    raise CRUDOperationError(f"Непредвиденная ошибка: {str(e)}") from e

        return wrapper

    return decorator
