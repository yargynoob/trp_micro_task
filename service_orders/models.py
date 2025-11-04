import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID
from database import Base

class Order(Base):
    __tablename__ = 'orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    items = Column(JSON, nullable=False)
    status = Column(String, default='created', nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Преобразование модели в словарь"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'items': self.items,
            'status': self.status,
            'total_amount': float(self.total_amount),
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': self.updated_at.isoformat() + 'Z'
        }
