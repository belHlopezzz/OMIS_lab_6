"""
Модуль Pydantic схем для валидации данных API.
"""
from schemas.user import (
    UserBase, UserCreate, UserResponse, 
    Token, TokenData, LoginRequest
)
from schemas.equipment import (
    EquipmentBase, EquipmentCreate, EquipmentResponse,
    SensorBase, SensorCreate, SensorResponse,
    SensorDataBase, SensorDataCreate, SensorDataResponse
)
from schemas.maintenance import (
    MaintenanceRecordBase, MaintenanceRecordCreate, MaintenanceRecordResponse
)
from schemas.events import AlertResponse, EventResponse
from schemas.dashboard import DashboardStats, ChartDataPoint
from schemas.prediction import PredictionRequest, PredictionResponse

__all__ = [
    "UserBase", "UserCreate", "UserResponse",
    "Token", "TokenData", "LoginRequest",
    "EquipmentBase", "EquipmentCreate", "EquipmentResponse",
    "SensorBase", "SensorCreate", "SensorResponse",
    "SensorDataBase", "SensorDataCreate", "SensorDataResponse",
    "MaintenanceRecordBase", "MaintenanceRecordCreate", "MaintenanceRecordResponse",
    "AlertResponse", "EventResponse",
    "DashboardStats", "ChartDataPoint",
    "PredictionRequest", "PredictionResponse",
]

