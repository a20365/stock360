from typing import Optional

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: Optional[str]
    name: str
    email: EmailStr


class UserCreate(BaseModel):
    id: Optional[str]
    name: str
    email: EmailStr
    role: str


class UserInToken(BaseModel):
    sub: str
    role: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
