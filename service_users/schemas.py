from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from datetime import datetime

class UserRegister(BaseModel):
    """Схема для регистрации пользователя"""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return v

class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    """Схема для обновления профиля пользователя"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    """Схема ответа с данными пользователя"""
    id: str
    email: str
    name: str
    roles: List[str]
    created_at: str
    updated_at: str

class TokenResponse(BaseModel):
    """Схема ответа с токеном"""
    success: bool = True
    data: dict

class ErrorResponse(BaseModel):
    """Схема ответа с ошибкой"""
    success: bool = False
    error: dict
