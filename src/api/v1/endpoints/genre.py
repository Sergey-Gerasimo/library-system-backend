from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from uuid import UUID
from typing import List
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
    cache_key = f"get:genre:all"

    if cached_genres := await redis.get(cache_key):
        return [
            GenreInDB.model_validate_json(genre) for genre in json.loads(cached_genres)
        ]

    genres = await genre_service.get_all()

    genres_json = json.dumps([genre.model_dump_json() for genre in genres])
    await redis.setex(name=cache_key, time=55 * 60, value=genres_json)
    return genres


@router.get("/get")
async def get_genre(
    genre_id: UUID,
    user_id: UUID,
    genre_service: GenreService = Depends(get_genre_service),
    redis: Redis = Depends(get_redis),
) -> GenreInDB:
    cache_key = f"get:genre:{genre_id}"

    if cached_genre := await redis.get(cache_key):
        return GenreInDB.model_validate(json.loads(cached_genre))

    genre = await genre_service.get(id=genre_id)

    await redis.setex(name=cache_key, time=55 * 60, value=genre.model_dump_json())
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
