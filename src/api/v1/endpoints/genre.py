from fastapi import APIRouter, Depends
from uuid import UUID
from typing import List
from fastapi_cache.decorator import cache

from schemas import GenreCreate, GenreInDB, GenreUpdate
from api.dependencies import get_genre_service
from services.services import GenreService


router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("/get_all")
@cache(expire=60)
async def get_all_genre(
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> List[GenreInDB]:
    return await genre_service.get_all()


@router.get("/get")
@cache(expire=60)
async def get_genre(
    genre_id: UUID,
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> GenreInDB:
    return await genre_service.get(id=genre_id)


@router.put("/update")
async def update_genre(
    genre_id: UUID,
    genre_data: GenreUpdate,
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> GenreInDB:
    genre = await genre_service.update(
        id=genre_id,
        schema=genre_data,
    )

    return genre


@router.post("/create")
async def create_genre(
    user_id: UUID,
    genre_data: GenreCreate,
    genre_service: GenreService = Depends(get_genre_service),
):
    genre = await genre_service.create(schema=genre_data)
    return genre


@router.delete("/delete")
async def delete_genre(
    user_id: UUID,
    genre_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
) -> GenreInDB:
    genre = await genre_service.delete(id=genre_id)

    return genre
