from pydantic import BaseModel, Field, validator
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class OrderItem(BaseModel):
    """Схема позиции заказа"""
    product: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0, le=10000)
    price: Decimal = Field(..., gt=0, le=1000000)
    
    @validator('product')
    def validate_product(cls, v):
        if not v or not v.strip():
            raise ValueError('Product name cannot be empty')
        return v.strip()
    
    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return Decimal(str(v)).quantize(Decimal('0.01'))
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class OrderCreate(BaseModel):
    """Схема для создания заказа"""
    items: List[OrderItem] = Field(..., min_items=1, max_items=100)
    
    @validator('items')
    def validate_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Order must contain at least one item')
        if len(v) > 100:
            raise ValueError('Order cannot contain more than 100 items')
        return v

class OrderUpdate(BaseModel):
    """Схема для обновления заказа"""
    status: Optional[str] = Field(None, pattern='^(created|processing|completed|cancelled)$')
    items: Optional[List[OrderItem]] = Field(None, min_items=1, max_items=100)
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['created', 'processing', 'completed', 'cancelled']
            if v not in allowed_statuses:
                raise ValueError(f'Invalid status. Allowed: {allowed_statuses}')
        return v

class OrderStatusUpdate(BaseModel):
    """Схема для обновления только статуса"""
    status: str = Field(..., pattern='^(created|processing|completed|cancelled)$')
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['created', 'processing', 'completed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'Invalid status. Allowed: {allowed_statuses}')
        return v

class OrderSearch(BaseModel):
    """Схема для поиска заказов"""
    user_id: Optional[str] = None
    status: Optional[str] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    page: int = Field(1, ge=1)
    per_page: int = Field(10, ge=1, le=100)
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['created', 'processing', 'completed', 'cancelled']
            if v not in allowed_statuses:
                raise ValueError(f'Invalid status. Allowed: {allowed_statuses}')
        return v

class OrderResponse(BaseModel):
    """Схема ответа с данными заказа"""
    id: str
    user_id: str
    items: List[dict]
    status: str
    total_amount: float
    created_at: str
    updated_at: str

class SuccessResponse(BaseModel):
    """Схема успешного ответа"""
    success: bool = True
    data: dict

class ErrorResponse(BaseModel):
    """Схема ответа с ошибкой"""
    success: bool = False
    error: dict

class PaginatedResponse(BaseModel):
    """Схема для пагинированных ответов"""
    success: bool = True
    data: List[dict]
    pagination: dict
