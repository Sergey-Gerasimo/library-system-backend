from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse, RedirectResponse
from utils.logger import log_decorator, ContextLogger
from redis import Redis

from uuid import UUID
from services.services import StorageService
from api.dependencies import get_storage_service, get_redis
from schemas import FileType

router = APIRouter(prefix="/download", tags=["download"])


@router.get("/book/{book_id}/pdf")
@log_decorator
async def download_book(
    book_id: UUID,
    storage_service: StorageService = Depends(get_storage_service),
    redis: Redis = Depends(get_redis),
):

    cache_key = f"download_link:pdf:{book_id}"

    if chached_url := await redis.get(cache_key):
        return RedirectResponse(url=chached_url)

    files = await storage_service.get_book_files(book_id)

    if not files:
        raise HTTPException(status_code=404, detail="Book not found")

    pdf_file = None

    for file in sorted(files, key=lambda x: x.created_at):
        if file.file_type == FileType.PDF:
            pdf_file = file
            break

    if not pdf_file:
        raise HTTPException(status_code=404, detail="pdf not found for this book")

    try:
        download_url = await storage_service.generate_download_link(
            file_key=pdf_file.storage_key,
            expires_in=3600,
            download_filename=pdf_file.original_name,
        )

        await redis.setex(name=cache_key, time=55 * 60, value=download_url)

        return RedirectResponse(url=download_url)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download book: {str(e)}"
        )


@router.get("/book/{book_id}/cover")
@log_decorator
async def download_cover(
    book_id: UUID,
    storage_service: StorageService = Depends(get_storage_service),
    redis: Redis = Depends(get_redis),
):

    cache_key = f"downlad_link:cover:{book_id}"

    if chached_url := await redis.get(cache_key):
        return RedirectResponse(url=chached_url)

    files = await storage_service.get_book_files(book_id)

    if not files:
        raise HTTPException(status_code=404, detail="cover not found")

    cover_file = None

    for file in sorted(files, key=lambda x: x.created_at):
        if file.file_type == FileType.COVER:
            cover_file = file
            break

    if not cover_file:
        raise HTTPException(
            status_code=404, detail="cover image not found for this book"
        )

    try:
        download_url = await storage_service.generate_download_link(
            file_key=cover_file.storage_key,
            expires_in=3600,
            download_filename=cover_file.original_name,
        )

        await redis.setex(name=cache_key, time=55 * 60, value=download_url)

        return RedirectResponse(url=download_url)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download cover: {str(e)}"
        )
