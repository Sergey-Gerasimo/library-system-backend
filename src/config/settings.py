from envparse import Env

env = Env()

class AppSettings:
    """Общие настройки приложения"""
    APP_NAME: str = env.str("APP_NAME", default="GUAP library servie")
    APP_VERSION: str = env.str("APP_VERSION", default="1.0.0")
    DEBUG: bool = env.bool("DEBUG", default=False)
    MAIN_API_BASE_URL: str = env.str("MAIN_API_BASE_URL")

app_settings = AppSettings()
