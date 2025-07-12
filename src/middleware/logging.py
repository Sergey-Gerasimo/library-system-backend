from loguru import logger
from fastapi import Request, Response
from time import time
import json

MAX_LENTGHT_BODY = 256


async def logging_middleware(request: Request, call_next):
    """
    Middleware для логирования запросов и ответов
    """
    start_time = time()

    # Логируем входящий запрос
    request_body = await request.body()
    logger.info(
        "Incoming request",
        payload={
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "body": request_body.decode()[:MAX_LENTGHT_BODY] if request_body else None,
        },
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        # Логируем исключения
        logger.error(
            f"Request failed: {str(exc)}",
            payload={
                "method": request.method,
                "url": str(request.url),
            },
        )
        raise

    # Логируем ответ
    process_time = time() - start_time
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    logger.info(
        "Request completed",
        payload={
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": process_time,
            "response_headers": dict(response.headers),
            "response_body": (
                response_body.decode()[:MAX_LENTGHT_BODY] if response_body else None
            ),
        },
    )

    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )
