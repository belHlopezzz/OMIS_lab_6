"""
Pydantic схемы для оборудования и датчиков.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field

from models.equipment import EquipmentStatus, SensorType


class SensorDataBase(BaseModel):
    """Базовые поля данных датчика."""
    value: float
    unit: str


class SensorDataCreate(SensorDataBase):
    """Схема для создания записи данных."""
    sensor_id: int


class SensorDataResponse(SensorDataBase):
    """Ответ с данными датчика."""
    id: int
    data_id: str
    timestamp: datetime
    sensor_id: int
    
    class Config:
        from_attributes = True


class SensorBase(BaseModel):
    """Базовые поля датчика."""
    type: SensorType
    location: Optional[str] = None


class SensorCreate(SensorBase):
    """Схема для создания датчика."""
    equipment_id: int
    calibration_date: Optional[date] = None


class SensorResponse(SensorBase):
    """Ответ с данными датчика."""
    id: int
    sensor_id: str
    calibration_date: Optional[date] = None
    equipment_id: int
    latest_value: Optional[float] = None
    latest_unit: Optional[str] = None
    latest_timestamp: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EquipmentBase(BaseModel):
    """Базовые поля оборудования."""
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = None
    description: Optional[str] = None


class EquipmentCreate(EquipmentBase):
    """Схема для создания оборудования."""
    installation_date: Optional[date] = None


class EquipmentResponse(EquipmentBase):
    """Ответ с данными оборудования."""
    id: int
    equipment_id: str
    status: EquipmentStatus
    installation_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    sensors: List[SensorResponse] = []
    
    class Config:
        from_attributes = True


class EquipmentWithMetrics(EquipmentResponse):
    """Оборудование с текущими метриками."""
    current_metrics: dict = {}
    last_update: Optional[datetime] = None

