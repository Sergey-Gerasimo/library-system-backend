import logging
from loguru import logger
import sys
import json
from pathlib import Path
from typing import Any, Dict
import asyncio
from utils.loki_sink import LokiHandler

from config.settings import app_settings
from config.loki_conf import loki_conf


def serialize(record: Dict[str, Any]) -> str:
    """
    Сериализация логов в JSON для структурированного логирования
    """
    subset = {
        "timestamp": record["time"].timestamp(),
        "message": record["message"],
        "level": record["level"].name,
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }

    # Добавляем exception информацию, если есть
    if record["exception"] is not None:
        subset["exception"] = repr(record["exception"])

    return json.dumps(subset)


def formatter(record: Dict[str, Any]) -> str:
    """
    Форматирование логов для консоли (более читабельный вид)
    """
    if record["extra"].get("payload") is not None:
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>\n{extra[payload]}\n"
        )
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>\n"
    )


def setup_logging(
    log_level: str = "INFO" if not app_settings.DEBUG else "DEBUG",
    log_file: str = app_settings.LOG_FILE,
    rotation: str = app_settings.ROTATION,
    retention: str = app_settings.RERETENTION,
    serialize_logs: bool = app_settings.SERIALIZE_LOG,
):
    """
    Настройка логгера

    :param log_level: Уровень логирования
    :param log_file: Путь к файлу логов
    :param rotation: Ротация логов (по размеру или времени)
    :param retention: Время хранения логов
    :param serialize_logs: Сериализовать ли логи в JSON
    """
    # Очищаем все существующие обработчики
    logger.remove()

    # Создаем директорию для логов, если ее нет
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Настройка формата в зависимости от флага сериализации
    format_func = serialize if serialize_logs else formatter

    # Добавляем обработчик для консоли
    logger.add(
        sys.stderr,
        level=log_level,
        format=format_func,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Добавляем обработчик для файла
    logger.add(
        log_file,
        level=log_level,
        format=format_func,
        rotation=rotation,
        retention=retention,
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Асинхронная запись логов
        serialize=False,
    )

    loki_handler = LokiHandler(
        url="http://loki:3100",
        tags={
            "application": app_settings.APP_NAME,
            "envirement": app_settings.ENVIREMENT,
            "service": "backend",
        },
        batch_size=20,
        batch_interval=3,
    )
    logger.add(loki_handler, format="{message}", level="INFO")

    # Настройка для UVICORN логов
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]

    return logger


class InterceptHandler(logging.Handler):
    """
    Перехват стандартных логов Python и перенаправление в Loguru
    """

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )
