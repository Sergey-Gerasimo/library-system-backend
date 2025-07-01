from fastapi import APIRouter
from api.v1.endpoints import auth, user, book, author, genre, download

api_router = APIRouter(prefix="/v1", tags=["v1"])
api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(book.router)
api_router.include_router(author.router)
api_router.include_router(genre.router)
api_router.include_router(download.router)
