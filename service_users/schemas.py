from pydantic import BaseModel, EmailStr, Field, validator, field_validator
from typing import List, Optional
from datetime import datetime
import re

class UserRegister(BaseModel):
    """Схема для регистрации пользователя"""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if len(v) > 100:
            raise ValueError('Password is too long')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v.strip()

class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    """Схема для обновления профиля пользователя"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Name cannot be empty')
            if len(v.strip()) < 2:
                raise ValueError('Name must be at least 2 characters')
        return v.strip() if v else v

class PasswordChange(BaseModel):
    """Схема для изменения пароля"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)
    
    @validator('new_password')
    def validate_new_password(cls, v, values):
        if 'old_password' in values and v == values['old_password']:
            raise ValueError('New password must be different from old password')
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters')
        return v

class UserRoleUpdate(BaseModel):
    """Схема для обновления ролей пользователя (только admin)"""
    roles: List[str] = Field(..., min_items=1)
    
    @validator('roles')
    def validate_roles(cls, v):
        allowed_roles = ['user', 'admin']
        for role in v:
            if role not in allowed_roles:
                raise ValueError(f'Invalid role: {role}. Allowed roles: {allowed_roles}')
        return v

class UserSearch(BaseModel):
    """Схема для поиска пользователей"""
    query: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=100)
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None and v not in ['user', 'admin']:
            raise ValueError('Invalid role')
        return v

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

class SuccessResponse(BaseModel):
    """Базовая схема успешного ответа"""
    success: bool = True
    data: dict

class PaginatedResponse(BaseModel):
    """Схема для пагинированных ответов"""
    success: bool = True
    data: List[dict]
    pagination: dict
