from envparse import Env
import os


env = Env()


class AppSettings:
    """Общие настройки приложения"""

    APP_NAME: str = env.str("APP_NAME", default="GUAP library servie")
    APP_VERSION: str = env.str("APP_VERSION", default="1.0.0")
    APP_HOST: str = env.str("APP_HOST", default="0.0.0.0")
    APP_PORT: int = env.int("APP_PORT", default=8000)
    APP_RELOAD: bool = env.bool("APP_RELOAD", default=False)

    DEBUG: bool = env.bool("DEBUG", default=False)
    LOG_FILE: str = os.path.join(env.str("LOG_PATH", default="./log"), "app.log")
    ROTATION: str = env.str("LOG_ROTATION", default="100 MB")
    RERETENTION: str = env.str("LOG_RERETENTION", default="30 days")
    SERIALIZE_LOG: bool = env.bool("SERIALIZE_LOG", default=False)


app_settings = AppSettings()
