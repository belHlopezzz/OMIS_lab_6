"""
Модуль роутеров FastAPI.
"""
from routers.auth import router as auth_router
from routers.equipment import router as equipment_router
from routers.sensors import router as sensors_router
from routers.events import router as events_router
from routers.reports import router as reports_router
from routers.dashboard import router as dashboard_router
from routers.predictions import router as predictions_router

__all__ = [
    "auth_router",
    "equipment_router", 
    "sensors_router",
    "events_router",
    "reports_router",
    "dashboard_router",
    "predictions_router",
]

