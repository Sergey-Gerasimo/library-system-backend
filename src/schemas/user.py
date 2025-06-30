from enum import Enum
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID


class User(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    roles: list[str] = list()


class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    hashed_password: str
    roles: List[UserRole] = []
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    hashed_password: Optional[str] = None
    roles: Optional[List[UserRole]] = None
    is_active: Optional[bool] = None


class UserFilter(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    id: UUID
    roles: List[UserRole]
    is_active: bool

    class Config:
        from_attributes = True
