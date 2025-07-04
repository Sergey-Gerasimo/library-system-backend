from loguru import logger
from functools import wraps
from typing import Callable, Any

# BUG:  --- Logging error in Loguru Handler #2 ---
# app-1       | Record was: {'elapsed': datetime.timedelta(seconds=40, microseconds=475050), 'exception': None, 'extra': {'payload': {'args': (), 'kwargs': {'storage_service': <services.services.storage_sevice.StorageService object at 0xffff86b32570>, 'book_id': UUID('7c9a8bad-b800-422d-b98b-2fae59d2145a')}}}, 'file': (name='logger.py', path='/app/utils/logger.py'), 'function': 'wrapper', 'level': (name='DEBUG', no=10, icon='🐞'), 'line': 13, 'message': 'Calling download_book', 'module': 'logger', 'name': 'utils.logger', 'process': (id=7, name='MainProcess'), 'thread': (id=281473044557856, name='MainThread'), 'time': datetime(2025, 7, 1, 21, 17, 36, 723613, tzinfo=datetime.timezone(datetime.timedelta(0), 'UTC'))}
# app-1       | Traceback (most recent call last):
# app-1       |   File "/usr/local/lib/python3.12/site-packages/loguru/_handler.py", line 204, in emit
# app-1       |     self._queue.put(str_record)
# app-1       |   File "/usr/local/lib/python3.12/multiprocessing/queues.py", line 393, in put
# app-1       |     obj = _ForkingPickler.dumps(obj)
# app-1       |           ^^^^^^^^^^^^^^^^^^^^^^^^^^
# app-1       |   File "/usr/local/lib/python3.12/multiprocessing/reduction.py", line 51, in dumps
# app-1       |     cls(buf, protocol).dump(obj)
# app-1       | AttributeError: Can't get local object '_createenviron.<locals>.encode'
# app-1       | --- End of logging error ---

# TODO: нужно учесть что не все объекты можно сериализовать


def log_decorator(func: Callable) -> Callable:
    """
    Декоратор для логирования вызовов функций
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        safe_kwargs = {k: v for k, v in kwargs.items() if not k.endswith("_service")}

        logger.debug(
            f"Calling {func.__name__}",
            payload={
                "args": args,
                "kwargs": safe_kwargs,
            },
        )
        try:
            result = await func(*args, **kwargs)
            logger.debug(
                f"Function {func.__name__} completed",
                payload={
                    "result": str(result)[:200],  # Ограничиваем длину лога
                },
            )
            return result
        except Exception as e:
            logger.error(
                f"Function {func.__name__} failed",
                payload={
                    "error": str(e),
                },
            )
            raise

    return wrapper


class ContextLogger:
    """
    Логгер с контекстом для сложных операций
    """

    def __init__(self, context: str):
        self.context = context

    def log(self, level: str, message: str, **kwargs):
        getattr(logger, level)(
            f"[{self.context}] {message}",
            payload=kwargs if kwargs else None,
        )

    def debug(self, message: str, **kwargs):
        self.log("debug", message, **kwargs)

    def info(self, message: str, **kwargs):
        self.log("info", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log("warning", message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log("error", message, **kwargs)

    def critical(self, message: str, **kwargs):
        self.log("critical", message, **kwargs)
