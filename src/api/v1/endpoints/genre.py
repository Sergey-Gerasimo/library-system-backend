from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from uuid import UUID
from typing import List
from fastapi_cache.decorator import cache
from redis import Redis
import json

from schemas import GenreCreate, GenreInDB, GenreUpdate
from api.dependencies import get_genre_service, get_redis
from services.services import GenreService


router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("/get_all")
async def get_all_genre(
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
    redis: Redis = Depends(get_redis),
) -> List[GenreInDB]:
    cache_key = f"genres:all:user"

    # Проверяем кэш
    if cached := await redis.get(cache_key):
        return [GenreInDB.model_validate_json(item) for item in json.loads(cached)]

    genres = await genre_service.get_all()

    await redis.setex(
        cache_key,
        60 * 60 * 24,
        json.dumps([jsonable_encoder(genre) for genre in genres]),
    )

    return genres


@router.get("/get")
async def get_genre(
    genre_id: UUID,
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
    redis: Redis = Depends(get_redis),
) -> GenreInDB:
    cache_key = f"genre:{genre_id}:user:{user_id}"

    if cached := await redis.get(cache_key):
        return GenreInDB.model_validate_json(cached)

    genre = await genre_service.get(id=genre_id)

    await redis.setex(cache_key, 60 * 60 * 12, genre.model_dump_json())  # 12 часов

    return genre


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
