"""
Настройка подключения к базе данных SQLAlchemy.
Используем SQLite для локального развёртывания.
"""

import logging

from config import DATABASE_URL
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Создаём движок БД с поддержкой многопоточности для SQLite
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db():
    """
    Генератор сессии БД для использования в зависимостях FastAPI.
    Автоматически закрывает сессию после использования.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Инициализация базы данных - создание всех таблиц.
    Вызывается при старте приложения.
    """
    # Импортируем все модели чтобы они зарегистрировались в Base.metadata
    from models.equipment import Alert, Equipment, Sensor, SensorData  # noqa: F401
    from models.maintenance import MaintenanceRecord  # noqa: F401
    from models.user import Administrator, Manager, Operator, User  # noqa: F401

    # Создаём все таблицы
    Base.metadata.create_all(bind=engine)

    # Логируем созданные таблицы
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"Таблицы в базе данных: {tables}")
    print(f"[DB] Таблицы в базе данных: {tables}")
