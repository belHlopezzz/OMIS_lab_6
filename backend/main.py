"""
Главный модуль приложения FastAPI.
Точка входа для запуска сервера.
"""

import asyncio
from contextlib import asynccontextmanager

from database import SessionLocal, init_db
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers import (
    auth_router,
    dashboard_router,
    equipment_router,
    events_router,
    predictions_router,
    reports_router,
    sensors_router,
)
from services.data_collection import DataCollectionSubsystem
from services.seed import seed_database

# Глобальная ссылка на задачу генерации данных
data_generation_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Инициализирует БД и запускает фоновые задачи при старте,
    корректно завершает их при остановке.
    """
    global data_generation_task

    # Инициализация при старте
    init_db()

    # Заполняем БД начальными данными
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    # Запускаем фоновую генерацию данных датчиков
    data_collector = DataCollectionSubsystem()
    data_generation_task = asyncio.create_task(data_collector.start_data_collection())

    yield

    # Завершение при остановке
    if data_generation_task:
        data_generation_task.cancel()
        try:
            await data_generation_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="IoT Monitor API",
    description="API системы прогнозирования поломок оборудования",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка CORS для взаимодействия с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все origins для разработки
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router, prefix="/api/auth", tags=["Аутентификация"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Дашборд"])
app.include_router(equipment_router, prefix="/api/equipment", tags=["Оборудование"])
app.include_router(sensors_router, prefix="/api/sensors", tags=["Датчики"])
app.include_router(events_router, prefix="/api/events", tags=["События"])
app.include_router(reports_router, prefix="/api/reports", tags=["Отчёты"])
app.include_router(
    predictions_router, prefix="/api/predictions", tags=["Прогнозирование"]
)


@app.get("/api/health")
async def health_check():
    """Проверка работоспособности сервера."""
    return {"status": "ok", "message": "Сервер работает"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
