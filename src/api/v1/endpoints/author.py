from fastapi import APIRouter, Depends
from uuid import UUID
from typing import List
from redis import Redis
import json

from schemas import AuthorCreate, AuthorInDB, AuthorUpdate
from api.dependencies import get_author_service, get_redis
from services.services import AuthorService


router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/get")
async def get_auther(
    author_id: UUID,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
    redis: Redis = Depends(get_redis),
) -> AuthorInDB:

    cache_key = f"author:{author_id}"

    if cached := await redis.get(cache_key):
        return AuthorInDB.model_validate_json(cached)

    author = await author_service.get(id=author_id)

    await redis.setex(
        cache_key,
        60 * 5,
        author.model_dump_json(),
    )

    return author


@router.get("/get_all")
async def get_all_authors(
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
    redis: Redis = Depends(get_redis),
) -> List[AuthorInDB]:

    cache_key = f"author:all"

    if cached_authors := await redis.get(cache_key):
        return [
            AuthorInDB.model_validate_json(author)
            for author in json.loads(cached_authors)
        ]

    authors = await author_service.get_all()

    authors_json = json.dumps([author.model_dump_json() for author in authors])
    await redis.setex(name=cache_key, time=55 * 60, value=authors_json)

    return authors


@router.put("/update")
async def update_author(
    author_id: UUID,
    author_data: AuthorUpdate,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
) -> AuthorInDB:

    author = await author_service.update(id=author_id, schema=author_data)

    return author


@router.post("/add")
async def add_author(
    author_data: AuthorCreate,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
) -> AuthorInDB:

    author = await author_service.create(schema=author_data)
    return author


@router.delete("/delete")
async def delete_author(
    author_id: UUID,
    user_id: UUID,
    author_service: AuthorService = Depends(get_author_service),
):
    await author_service.delete(id=author_id)
