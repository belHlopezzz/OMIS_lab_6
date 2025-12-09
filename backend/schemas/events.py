"""
Pydantic схемы для событий и оповещений.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from models.equipment import AlertSeverity


class AlertResponse(BaseModel):
    """Ответ с данными оповещения."""
    id: int
    alert_id: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    equipment_id: int
    equipment_name: Optional[str] = None
    sensor_id: Optional[int] = None
    is_read: bool
    is_email_sent: bool
    
    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    """Унифицированный формат события для фронтенда."""
    id: int
    type: str  # critical, warning
    device: str  # название оборудования
    message: str
    timestamp: str  # форматированная дата

