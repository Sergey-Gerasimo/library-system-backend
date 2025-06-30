from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


from schemas import BookInDB, BookCreate, BookUpdate, File as UniversalFile
from api.dependencies import get_book_service
from services.services import BookService

from typing import Annotated, Optional

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/add")
async def create_book(
    book: Annotated[BookCreate, Depends()],
    user_id: Annotated[UUID, Form(...)],
    pdf_file: UploadFile = File(...),
    cover: UploadFile = File(...),
    book_service: BookService = Depends(get_book_service),
) -> BookInDB:

    pdf_file = await UniversalFile.from_uploadfile(pdf_file)
    cover = await UniversalFile.from_uploadfile(cover)

    book = await book_service.create(pdf=pdf_file, cover=cover, book=book)

    return book


@router.get("/get")
async def get_book(
    book_id: UUID,
    book_service: BookService = Depends(get_book_service),
) -> BookInDB:
    book = await book_service.get(id=book_id)
    return book


@router.put("/update")
async def update_book(
    book_id: Annotated[UUID, Form(..., description="UUID книги для обновления")],
    book_data: Annotated[
        str, Form(..., description="JSON строка с данными для обновления (BookUpdate)")
    ],
    user_id: Annotated[
        UUID, Form(..., description="UUID пользователя, инициирующего обновление")
    ],
    new_pdf: Annotated[
        Optional[UploadFile], File(description="Новый PDF файл книги")
    ] = None,
    new_cover: Annotated[
        Optional[UploadFile], File(description="Новая обложка книги")
    ] = None,
    book_service: BookService = Depends(get_book_service),
) -> BookInDB:
    if new_pdf is not None:
        new_pdf = await UniversalFile.from_uploadfile(new_pdf)

    if new_cover is not None:
        new_cover = await UniversalFile.from_uploadfile(new_cover)

    book = await book_service.update(
        id=book_id, pdf=new_pdf, cover=new_cover, book=book_data
    )
    return book


@router.delete("/delete")
async def delete_book(
    book_id: UUID,
    user_id: UUID,
    book_service: BookService = Depends(get_book_service),
) -> BookInDB:

    book = await book_service.delete(id=book_id)
    return book
