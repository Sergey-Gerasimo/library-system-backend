from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from redis import Redis
import json

from schemas import BookInDB, BookCreate, BookUpdate, File as UniversalFile
from api.dependencies import get_book_service, get_redis
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
    redis: Redis = Depends(get_redis),
) -> BookInDB:

    cache_key = f"book:{book_id}"

    if cached := await redis.get(cache_key):
        return BookInDB.model_validate_json(cached)

    book = await book_service.get(id=book_id)

    await redis.setex(cache_key, 60 * 15, book.model_dump_json())
    return book


@router.get("/get_all")
async def get_all_books(
    book_service: BookService = Depends(get_book_service),
    redis: Redis = Depends(get_redis),
) -> list[BookInDB]:
    cache_key = "books:all"

    if cached := await redis.get(cache_key):
        return [BookInDB.model_validate_json(item) for item in json.loads(cached)]

    books = await book_service.get_all()

    await redis.setex(
        cache_key, 60 * 5, json.dumps([book.model_dump() for book in books])
    )

    return books


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
