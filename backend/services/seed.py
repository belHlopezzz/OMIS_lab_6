"""
Сервис заполнения базы данных начальными данными.
Создаёт демо-пользователей, оборудование и датчики.
"""
import uuid
from datetime import date, datetime, timedelta
import random

from sqlalchemy.orm import Session

from models.user import User, UserRole
from models.equipment import Equipment, Sensor, SensorData, EquipmentStatus, SensorType
from models.maintenance import MaintenanceRecord
from utils.auth import get_password_hash


def generate_id() -> str:
    """Генерация уникального короткого ID."""
    return str(uuid.uuid4())[:8]


def seed_database(db: Session):
    """
    Заполнение базы данных начальными данными.
    Выполняется только если база пустая.
    """
    # Проверяем, есть ли уже пользователи
    existing_users = db.query(User).first()
    if existing_users:
        return  # база уже заполнена
    
    # Создаём демо-пользователей
    _create_demo_users(db)
    
    # Создаём оборудование с датчиками
    equipment_list = _create_demo_equipment(db)
    
    # Генерируем исторические данные датчиков
    _create_historical_sensor_data(db, equipment_list)
    
    # Создаём записи об обслуживании
    _create_demo_maintenance_records(db, equipment_list)
    
    db.commit()


def _create_demo_users(db: Session):
    """Создание демонстрационных пользователей."""
    users = [
        {
            "user_id": f"USR-{generate_id()}",
            "username": "Иван Петров",
            "email": "operator@test.com",
            "password_hash": get_password_hash("operator123"),
            "user_type": UserRole.OPERATOR,
            "department": "Цех №1",
        },
        {
            "user_id": f"USR-{generate_id()}",
            "username": "Анна Сидорова",
            "email": "admin@test.com",
            "password_hash": get_password_hash("admin123"),
            "user_type": UserRole.ADMINISTRATOR,
            "access_level": 10,
        },
        {
            "user_id": f"USR-{generate_id()}",
            "username": "Сергей Козлов",
            "email": "manager@test.com",
            "password_hash": get_password_hash("manager123"),
            "user_type": UserRole.MANAGER,
            "role_description": "Главный инженер",
        },
        {
            "user_id": f"USR-{generate_id()}",
            "username": "Игнат Тестов",
            "email": "telezboez@gmail.com",
            "password_hash": get_password_hash("test123"),
            "user_type": UserRole.ADMINISTRATOR,
            "access_level": 10,
        },
    ]
    
    for user_data in users:
        user = User(**user_data)
        db.add(user)
    
    db.flush()


def _create_demo_equipment(db: Session) -> list:
    """Создание демонстрационного оборудования с датчиками."""
    equipment_configs = [
        {"name": "Турбина #1", "type": "Турбина", "location": "Цех №1"},
        {"name": "Турбина #3", "type": "Турбина", "location": "Цех №1", "status": EquipmentStatus.ERROR},
        {"name": "Компрессор #1", "type": "Компрессор", "location": "Цех №2", "status": EquipmentStatus.ERROR},
        {"name": "Компрессор #4", "type": "Компрессор", "location": "Цех №2"},
        {"name": "Насос #3", "type": "Насос", "location": "Цех №3"},
        {"name": "Насос #7", "type": "Насос", "location": "Цех №3", "status": EquipmentStatus.OFFLINE},
        {"name": "Электродвигатель #5", "type": "Электродвигатель", "location": "Цех №1"},
        {"name": "Конвейер #2", "type": "Конвейер", "location": "Цех №2"},
    ]
    
    equipment_list = []
    
    for config in equipment_configs:
        eq = Equipment(
            equipment_id=f"EQ-{generate_id()}",
            name=config["name"],
            type=config["type"],
            location=config.get("location"),
            status=config.get("status", EquipmentStatus.ONLINE),
            installation_date=date.today() - timedelta(days=random.randint(100, 1000)),
        )
        db.add(eq)
        db.flush()
        
        # Добавляем датчики для каждого оборудования
        _create_sensors_for_equipment(db, eq)
        equipment_list.append(eq)
    
    return equipment_list


def _create_sensors_for_equipment(db: Session, equipment: Equipment):
    """Создание датчиков для единицы оборудования."""
    sensor_types = [
        (SensorType.TEMPERATURE, "°C"),
        (SensorType.VIBRATION, "мм/с"),
        (SensorType.PRESSURE, "кПа"),
        (SensorType.CURRENT, "А"),
    ]
    
    for sensor_type, unit in sensor_types:
        sensor = Sensor(
            sensor_id=f"SNS-{generate_id()}",
            type=sensor_type,
            location=f"{equipment.location}, {equipment.name}",
            calibration_date=date.today() - timedelta(days=random.randint(30, 180)),
            equipment_id=equipment.id,
        )
        db.add(sensor)
    
    db.flush()


def _create_historical_sensor_data(db: Session, equipment_list: list):
    """
    Создание исторических данных датчиков для обучения ML моделей.
    Генерируем данные за последние 7 дней с интервалом 30 минут.
    """
    # Базовые параметры для каждого типа датчика
    sensor_params = {
        SensorType.TEMPERATURE: {"base": 45, "variance": 15, "unit": "°C"},
        SensorType.VIBRATION: {"base": 2.5, "variance": 1.5, "unit": "мм/с"},
        SensorType.PRESSURE: {"base": 200, "variance": 50, "unit": "кПа"},
        SensorType.CURRENT: {"base": 20, "variance": 8, "unit": "А"},
    }
    
    now = datetime.utcnow()
    # Генерируем данные за последние 7 дней, каждые 30 минут
    time_points = []
    for hours_ago in range(7 * 24 * 2):  # 7 дней * 24 часа * 2 (каждые 30 мин)
        time_points.append(now - timedelta(minutes=hours_ago * 30))
    
    for equipment in equipment_list:
        # Определяем, должно ли оборудование показывать аномалии
        has_issues = equipment.status in (EquipmentStatus.ERROR, EquipmentStatus.OFFLINE)
        
        for sensor in equipment.sensors:
            params = sensor_params[sensor.type]
            
            for timestamp in time_points:
                # Базовое значение с нормальным шумом
                value = params["base"] + random.gauss(0, params["variance"] * 0.3)
                
                # Добавляем суточный цикл для температуры
                if sensor.type == SensorType.TEMPERATURE:
                    hour = timestamp.hour
                    value += 5 * (1 - abs(hour - 14) / 12)  # пик в 14:00
                
                # Добавляем аномалии для проблемного оборудования
                if has_issues and random.random() < 0.1:
                    value += params["variance"] * random.uniform(1.5, 3)
                
                # Гарантируем неотрицательность
                value = max(0, value)
                
                sensor_data = SensorData(
                    data_id=f"DAT-{generate_id()}",
                    timestamp=timestamp,
                    value=round(value, 2),
                    unit=params["unit"],
                    sensor_id=sensor.id,
                )
                db.add(sensor_data)
    
    db.flush()


def _create_demo_maintenance_records(db: Session, equipment_list: list):
    """Создание демонстрационных записей об обслуживании."""
    technicians = ["Петров И.В.", "Сидоров А.А.", "Козлов С.М."]
    maintenance_types = [
        "Плановое техническое обслуживание",
        "Замена фильтров",
        "Калибровка датчиков",
        "Смазка подшипников",
        "Проверка электрических соединений",
        "Замена уплотнителей",
    ]
    
    for equipment in equipment_list:
        # Создаём 2-4 записи на оборудование
        for _ in range(random.randint(2, 4)):
            record = MaintenanceRecord(
                record_id=f"MNT-{generate_id()}",
                date=date.today() - timedelta(days=random.randint(10, 180)),
                description=random.choice(maintenance_types),
                technician=random.choice(technicians),
                equipment_id=equipment.id,
                is_completed=1,
                completed_at=datetime.utcnow() - timedelta(days=random.randint(10, 180)),
            )
            db.add(record)
    
    db.flush()

