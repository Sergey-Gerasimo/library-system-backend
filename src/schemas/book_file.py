from typing import Optional
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, constr
from datetime import datetime


class FileType(str, Enum):
    COVER = "cover"
    PDF = "pdf"


class BookFileBase(BaseModel):
    book_id: UUID
    storage_key: str
    file_type: FileType
    original_name: str
    size_bytes: int = Field(..., gt=0)
    mime_type: str


class BookFileCreate(BookFileBase):
    pass


class BookFileUpdate(BaseModel):
    book_id: Optional[UUID] = None
    storage_key: Optional[str] = None
    file_type: Optional[FileType] = None
    original_name: Optional[str] = None
    size_bytes: Optional[int] = Field(None, gt=0)
    mime_type: Optional[str] = None


class BookFileFilter(BaseModel):
    book_id: Optional[UUID] = None
    file_type: Optional[FileType] = None
    mime_type: Optional[str] = None


class BookFileInDB(BookFileBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
