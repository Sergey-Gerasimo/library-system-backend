from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


from schemas import BookResponse, BookCreate, BookUpdate
from api.dependencies import get_book_service, get_db
from services import BookService


router = APIRouter(prefix="/books", tags=["books"])


@router.post("/create")
async def create_book(
    pdf_file: UploadFile,
    cover: UploadFile,
    book: BookCreate,
    user_id: UUID,
    book_service: BookService = Depends(get_book_service),
) -> BookResponse:

    book = await book_service.create_book(
        cover_file=cover,
        pdf_file=pdf_file,
        book_data=book,
        user_id=user_id,
    )

    return book


@router.get("/get")
async def get_book(
    book_id: UUID,
    book_service: BookService = Depends(get_book_service),
) -> BookResponse:
    book = await book_service.get_book(book_id=book_id)
    return book


@router.put("/update")
async def update_book(
    book_id: UUID,
    book_data: BookUpdate,
    user_id: UUID,
    book_service: BookService = Depends(get_book_service),
) -> BookResponse:
    book = await book_service.update_book(
        book_id=book_id,
        book_data=book_data,
        user_id=user_id,
    )
    return book


@router.delete("/delete")
async def delete_book(
    book_id: UUID,
    user_id: UUID,
    book_service: BookService = Depends(get_book_service),
) -> BookResponse:

    book = await book_service.delete_book(book_id=book_id, user_id=user_id)
    return book
