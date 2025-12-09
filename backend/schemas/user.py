"""
Pydantic схемы для пользователей и аутентификации.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from models.user import UserRole


class UserBase(BaseModel):
    """Базовые поля пользователя."""
    username: str = Field(..., min_length=2, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    """Схема для создания пользователя."""
    password: str = Field(..., min_length=6)
    user_type: UserRole
    department: Optional[str] = None
    access_level: Optional[int] = None
    role_description: Optional[str] = None


class UserResponse(UserBase):
    """Схема ответа с данными пользователя."""
    id: int
    user_id: str
    user_type: UserRole
    department: Optional[str] = None
    access_level: Optional[int] = None
    role_description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Запрос на вход в систему."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Токен доступа."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Данные из токена."""
    user_id: Optional[str] = None
    user_type: Optional[str] = None

