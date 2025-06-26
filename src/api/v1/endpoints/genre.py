from fastapi import APIRouter, Depends
from uuid import UUID
from typing import List

from schemas import GenreCreate, GenreInDB, GenreUpdate, GenreWithBooks
from api.dependencies import get_genre_service
from services import GenreService


router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("/get_all")
async def get_all_genre(
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> List[GenreInDB]:
    return await genre_service.get_all_genres()


@router.get("/get")
async def get_genre(
    genre_id: UUID,
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> GenreInDB:
    return await genre_service.get_genre_by_id(genre_id=genre_id)


@router.put("/update")
async def update_genre(
    genre_id: UUID,
    genre_data: GenreUpdate,
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> GenreInDB:
    genre = await genre_service.update_genre(
        genre_id=genre_id,
        genre_data=genre_data,
    )

    return genre


@router.post("/create")
async def create_genre(
    user_id: UUID,
    genre_data: GenreCreate,
    genre_service: GenreService = Depends(get_genre_service),
):
    genre = await genre_service.create_genre(
        genre_data=genre_data,
    )

    return genre


@router.delete("/delete")
async def delete_genre(
    user_id: UUID,
    genre_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> GenreInDB:
    genre = await genre_service.delete_genre(genre_id=genre_id)

    return genre
