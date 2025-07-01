from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse, RedirectResponse
import io

from uuid import UUID
from services.services import StorageService
from api.dependencies import get_storage_service
from schemas import FileType

router = APIRouter(prefix="/download", tags=["download"])


@router.get("/book/{book_id}/pdf")
async def download_book(
    book_id: UUID, storage_service: StorageService = Depends(get_storage_service)
):
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
            expires_in=3600,  # 1 час доступ
            download_filename=pdf_file.original_name,
        )

        # 4. Делаем редирект
        return RedirectResponse(url=download_url)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download book: {str(e)}"
        )


@router.get("/book/{book_id}/cover")
async def download_cover(
    book_id: UUID, storage_service: StorageService = Depends(get_storage_service)
):
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
            expires_in=3600,  # 1 час доступ
            download_filename=cover_file.original_name,
        )

        # 4. Делаем редирект
        return RedirectResponse(url=download_url)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download cover: {str(e)}"
        )
