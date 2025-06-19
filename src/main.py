from fastapi import FastAPI

from api.v1.routers import api_router
from config import app_settings


app = FastAPI(
    title=app_settings.APP_NAME,
    version=app_settings.APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
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
