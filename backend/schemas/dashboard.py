"""
Pydantic схемы для дашборда.
"""
from typing import List, Optional
from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Статистика для главной страницы."""
    total_devices: int
    online_devices: int
    error_devices: int
    offline_devices: int
    maintenance_devices: int
    total_alerts_today: int
    critical_alerts: int


class ChartDataPoint(BaseModel):
    """Точка данных для графика."""
    time: str
    value: float
    label: Optional[str] = None


class TemperatureChartData(BaseModel):
    """Данные для графика температуры."""
    data: List[ChartDataPoint]
    avg_value: float
    min_value: float
    max_value: float

