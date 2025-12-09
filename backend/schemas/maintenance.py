"""
Pydantic схемы для записей обслуживания.
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class MaintenanceRecordBase(BaseModel):
    """Базовые поля записи обслуживания."""
    description: str = Field(..., min_length=1)
    technician: str = Field(..., min_length=1)


class MaintenanceRecordCreate(MaintenanceRecordBase):
    """Схема для создания записи обслуживания."""
    equipment_id: int
    date: date


class MaintenanceRecordUpdate(BaseModel):
    """Схема для обновления записи обслуживания."""
    description: Optional[str] = None
    technician: Optional[str] = None
    notes: Optional[str] = None
    is_completed: Optional[bool] = None


class MaintenanceRecordResponse(MaintenanceRecordBase):
    """Ответ с данными записи обслуживания."""
    id: int
    record_id: str
    date: date
    equipment_id: int
    notes: Optional[str] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

