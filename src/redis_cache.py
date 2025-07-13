from redis import Redis
from fastapi import Request, Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from config import services_settings

# Подключение к Redis
redis = Redis(
    host=services_settings.REDIS_SETTINGS.HOST,
    port=services_settings.REDIS_SETTINGS.PORT,
    db=services_settings.REDIS_SETTINGS.DB,
    password=services_settings.REDIS_SETTINGS.PASSWORD,
    ssl=services_settings.REDIS_SETTINGS.IS_SSL,
    decode_responses=True,  # для автоматического декодирования в строки
)


# Инициализация кэша
def init_cache():
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
