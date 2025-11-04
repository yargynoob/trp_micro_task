from pydantic import BaseModel, Field, validator
from typing import List, Optional
from decimal import Decimal

class OrderItem(BaseModel):
    """Схема позиции заказа"""
    product: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)

class OrderCreate(BaseModel):
    """Схема для создания заказа"""
    user_id: str
    items: List[OrderItem] = Field(..., min_items=1)
    
    @validator('items')
    def validate_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Заказ должен содержать хотя бы одну позицию')
        return v

class OrderUpdate(BaseModel):
    """Схема для обновления статуса заказа"""
    status: str = Field(..., pattern='^(created|in_progress|completed|cancelled)$')

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
