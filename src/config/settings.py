from envparse import Env

env = Env()


class AppSettings:
    """Общие настройки приложения"""

    APP_NAME: str = env.str("APP_NAME", default="GUAP library servie")
    APP_VERSION: str = env.str("APP_VERSION", default="1.0.0")
    APP_HOST: str = env.str("APP_HOST", default="0.0.0.0")
    APP_PORT: int = env.int("APP_PORT", default=8000)
    APP_RELOAD: bool = env.bool("APP_RELOAD", default=False)

    DEBUG: bool = env.bool("DEBUG", default=False)
    MAIN_API_BASE_URL: str = env.str("MAIN_API_BASE_URL")


app_settings = AppSettings()
