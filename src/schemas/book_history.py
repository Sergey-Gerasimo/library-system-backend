from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
from uuid import UUID


class BookHistoryAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class BookHistoryBase(BaseModel):
    book_id: UUID
    user_id: UUID
    action: BookHistoryAction
    old_values: Optional[Dict] = None
    new_values: Optional[Dict] = None


class BookHistoryCreate(BookHistoryBase):
    pass


class BookHistoryFilter(BaseModel):
    book_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    action: Optional[BookHistoryAction] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class BookHistoryInDB(BookHistoryBase):
    id: UUID
    changed_at: datetime

    class Config:
        from_attributes = True


class BookHistoryUpdate(BaseModel):
    action: Optional[BookHistoryAction] = None
    old_values: Optional[Dict] = None
    new_values: Optional[Dict] = None
