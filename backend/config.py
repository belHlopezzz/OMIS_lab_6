"""
Конфигурация приложения.
Содержит настройки базы данных, JWT, email и ML моделей.
"""
import os
from pathlib import Path

# Загружаем переменные окружения из .env файла если он существует
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Config] Загружен .env файл: {env_path}")
except ImportError:
    # Если python-dotenv не установлен, просто читаем из окружения
    pass


# Базовые пути
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ML_MODELS_DIR = BASE_DIR / "ml" / "saved_models"

# Создаём директории если их нет
DATA_DIR.mkdir(exist_ok=True)
ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)

# База данных SQLite
DATABASE_URL = f"sqlite:///{DATA_DIR}/equipment.db"

# JWT настройки
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Email настройки (для тестирования используем Gmail SMTP)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@iotmonitor.local")

# Пороговые значения для датчиков
SENSOR_THRESHOLDS = {
    "temperature": {"warning": 70.0, "critical": 85.0, "unit": "°C"},
    "vibration": {"warning": 5.0, "critical": 7.5, "unit": "мм/с"},
    "pressure": {"warning": 350.0, "critical": 450.0, "unit": "кПа"},
    "current": {"warning": 35.0, "critical": 45.0, "unit": "А"},
}

# Интервал генерации данных (секунды)
# Интервал генерации данных (секунды)
# Для демонстрации сокращаем до 8 секунд, чтобы события появлялись быстрее.
DATA_GENERATION_INTERVAL = 8

# ML настройки
ML_PREDICTION_HORIZON_HOURS = 48
ANOMALY_PROBABILITY_THRESHOLD = 0.7

