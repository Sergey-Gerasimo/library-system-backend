from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum, ForeignKey, String, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Annotated, Optional, List
from datetime import datetime, timezone

from database import Base

get_current_time = lambda: datetime.now(timezone.utc)
idpk = Annotated[int, mapped_column(primary_key=True)]
created_at = Annotated[datetime, mapped_column(default=get_current_time)]


class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[idpk]
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    roles: Mapped[List[UserRole]] = mapped_column(SQLAlchemyEnum(UserRole), default=[])
    is_active: Mapped[bool] = mapped_column(default=True)

    changed_books: Mapped[List["BookHistory"]] = relationship(back_populates="user")


class FileType(str, Enum):
    COVER = "cover"
    PDF = "pdf"


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[idpk]
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    bio: Mapped[Optional[str]] = mapped_column(Text)

    books: Mapped[List["Book"]] = relationship(
        back_populates="author",
        lazy="raise",
    )


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[idpk]
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    books: Mapped[List["Book"]] = relationship(
        back_populates="genre",
        lazy="raise",
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[idpk]
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    genre_id: Mapped[Optional[int]] = mapped_column(ForeignKey("genres.id"))
    year: Mapped[int] = mapped_column(index=True)
    is_published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[created_at]

    author: Mapped["Author"] = relationship(
        back_populates="books",
        lazy="raise",
    )
    genre: Mapped[Optional["Genre"]] = relationship(
        back_populates="books",
        lazy="raise",
    )
    files: Mapped[List["BookFile"]] = relationship(
        back_populates="book",
        lazy="raise",
    )
    history: Mapped[List["BookHistory"]] = relationship(
        back_populates="book",
        lazy="raise",
    )


class BookFile(Base):
    __tablename__ = "book_files"

    id: Mapped[idpk]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)  # Путь в S3
    file_type: Mapped[FileType] = mapped_column(SQLAlchemyEnum(FileType))
    original_name: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int]
    mime_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[created_at]

    book: Mapped["Book"] = relationship(
        back_populates="files",
        lazy="raise",
    )


class BookHistoryAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class BookHistory(Base):
    __tablename__ = "book_history"

    id: Mapped[idpk]
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[BookHistoryAction] = mapped_column(SQLAlchemyEnum(BookHistoryAction))
    changed_at: Mapped[created_at]
    old_values: Mapped[Optional[dict]] = mapped_column(JSON)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON)

    book: Mapped["Book"] = relationship(
        back_populates="history",
        lazy="raise",
    )
    user: Mapped["User"] = relationship(
        back_populates="changed_books",
        lazy="raise",
    )
