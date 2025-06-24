from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.v1.routers import api_router
from config import app_settings

from database import create_tables, async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения.

    """
    await create_tables(async_engine)
    yield


app = FastAPI(
    title=app_settings.APP_NAME,
    version=app_settings.APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=app_settings.APP_HOST,
        port=app_settings.APP_PORT,
        reload=app_settings.APP_RELOAD,
    )
