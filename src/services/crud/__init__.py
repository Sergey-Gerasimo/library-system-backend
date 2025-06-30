from .user_crud import UserCRUD, IUserCRUD
from .book_files_crud import BookFilesCRUD, IBookFilesCRUD
from .book_crud import BookCRUD, IBookCRUD
from .book_history_crud import BookHistoryCRUD, IBookHistoryCRUD
from .author_crud import AuthorCRUD, IAuthorCRUD
from .s3_crud import S3CRUD, IStorageRUD
from .genre_crud import GenreCRUD, IGenreCRUD

__all__ = [
    "UserCRUD",
    "IUserCRUD",
    "BookCRUD",
    "IBookCRUD",
    "BookFilesCRUD",
    "IBookFilesCRUD",
    "BookHistoryCRUD",
    "IBookHistoryCRUD",
    "AuthorCRUD",
    "IAuthorCRUD",
    "S3CRUD",
    "IStorageRUD",
    "GenreCRUD",
    "IGenreCRUD",
]
