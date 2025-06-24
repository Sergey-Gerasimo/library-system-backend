from envparse import Env

env = Env()


class DBSettings:
    DB_HOST: str = env.str("POSTGRES_HOST", default="localhost")
    DB_PORT: int = env.int("POSTGRES_PORT", default=5432)
    DB_USER: str = env.str("POSTGRES_USER", default="postgres")
    DB_PASSWORD: str = env.str("POSTGRES_PASSWORD", default="postgres")
    DB_NAME: str = env.str("POSTGRES_DB", default="postgres")

    @property
    def DATABSE_URL_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def DATABSE_URL_psyconpg(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


db_settings = DBSettings()
