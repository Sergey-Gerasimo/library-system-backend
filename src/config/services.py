from envparse import Env
from typing import Optional

env = Env()


class RedisSettings:
    HOST: str = env.str("REDIS_HOST", default="localhost")
    PORT: int = env.int("REDIS_PORT", default=6379)
    DB: int = env.int("REDIS_DB", default=0)
    PASSWORD: Optional[str] = env.str("REDIS_PASSWORD", default=None)
    IS_SSL: bool = env.bool("IS_SSL", default=False)


class ServicesSettings:
    REDIS_SETTINGS = RedisSettings()


services_settings = ServicesSettings()
