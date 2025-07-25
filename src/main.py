from fastapi import FastAPI, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest
from contextlib import asynccontextmanager
from loguru import logger
from redis import Redis


from api.v1.routers import api_router
from api.dependencies import get_redis, init_redis_pool, close_redis_pool
from config import app_settings
from logging_conf import setup_logging
from middleware.metrics import metrics_middleware
from database import create_tables, async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Жизненный цикл приложения.

    """
    await create_tables(async_engine)
    await init_redis_pool()
    yield
    await close_redis_pool()


setup_logging()


app = FastAPI(
    title=app_settings.APP_NAME,
    version=app_settings.APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# app.middleware("http")(logging_middleware)
app.middleware("http")(metrics_middleware)
app.include_router(api_router, prefix="/api")


@app.get("/health/redis")
async def health_redis(redis: Redis = Depends(get_redis)):
    await redis.ping()
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return generate_latest()


if __name__ == "__main__":
    import uvicorn

    logger.success("Application started successfully")
    uvicorn.run(
        app,
        host=app_settings.APP_HOST,
        port=app_settings.APP_PORT,
        reload=app_settings.APP_RELOAD,
    )
