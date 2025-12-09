"""
Pydantic схемы для прогнозирования.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class PredictionRequest(BaseModel):
    """Запрос на прогнозирование."""
    equipment_id: int
    horizon_hours: int = 48  # горизонт прогноза в часах


class FailurePrediction(BaseModel):
    """Результат прогноза отказа."""
    probability: float  # вероятность отказа (0-1)
    confidence: float  # уверенность модели (0-1)
    time_window_hours: int  # временное окно прогноза
    risk_level: str  # low, medium, high, critical
    factors: List[str]  # факторы риска


class PredictionResponse(BaseModel):
    """Ответ с результатами прогнозирования."""
    equipment_id: int
    equipment_name: str
    prediction_time: datetime
    failure_prediction: FailurePrediction
    recommendations: List[str]
    current_status: str


class AnomalyDetectionResult(BaseModel):
    """Результат обнаружения аномалий."""
    is_anomaly: bool
    anomaly_score: float
    sensor_type: str
    current_value: float
    expected_range: List[float]
    message: Optional[str] = None

