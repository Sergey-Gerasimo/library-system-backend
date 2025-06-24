from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import BookResponse, BookCreate
from api.dependencies import get_book_service, get_db
from services.book_storage import BookStorage


router = APIRouter(prefix="/books", tags=["books"])


@router.post("/create")
async def create_book(
    pdf_file: UploadFile,
    cover: UploadFile,
    book: BookCreate,
    db_sevice: AsyncSession = Depends(get_db),
    book_service: BookStorage = Depends(get_book_service),
) -> BookResponse:

    pass
