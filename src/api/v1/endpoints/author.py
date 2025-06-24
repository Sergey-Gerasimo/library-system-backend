from fastapi import APIRouter, Depends
from uuid import UUID
from typing import List

from schemas import AuthorCreate, AuthorInDB, AuthorUpdate
from api.dependencies import get_author_service
from services import AuthorService


router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/get")
async def get_auther(
    author_id: UUID,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
) -> AuthorInDB:

    author = await author_service.get_author_by_id(author_id=author_id)
    return author


@router.get("/get_all")
async def get_all_authors(
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
) -> List[AuthorInDB]:
    authors = await author_service.get_all_authors()

    return authors


@router.put("/update")
async def update_author(
    author_id: UUID,
    author_data: AuthorUpdate,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
) -> AuthorInDB:

    author = await author_service.update_author(
        author_id=author_id, author_data=author_data
    )

    return author


@router.post("/add")
async def add_author(
    author_data: AuthorCreate,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
) -> AuthorInDB:
    author = await author_service.create_author(author_data=author_data)

    return author


@router.delete("/delete")
async def delete_author(
    author_id: UUID,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
) -> AuthorInDB:

    author = await author_service.delete_author(author_id=author_id)
    return author
