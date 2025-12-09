"""
Модели оборудования, датчиков и данных.
Реализация сущностей из UML диаграммы: Equipment, Sensor, SensorData.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Date, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from database import Base


class EquipmentStatus(enum.Enum):
    """Статусы оборудования."""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class SensorType(enum.Enum):
    """Типы датчиков."""
    TEMPERATURE = "temperature"
    VIBRATION = "vibration"
    PRESSURE = "pressure"
    CURRENT = "current"


class AlertSeverity(enum.Enum):
    """Уровни критичности оповещений."""
    WARNING = "warning"
    CRITICAL = "critical"


class Equipment(Base):
    """
    Оборудование.
    
    Атрибуты из диаграммы:
    - equipmentId: String - идентификатор
    - name: String - название
    - type: String - тип оборудования
    - status: String - текущий статус
    - installationDate: Date - дата установки
    
    Методы из диаграммы:
    - getCurrentMetrics() - получение текущих метрик
    - getMaintenanceHistory() - получение истории обслуживания
    
    Связи из диаграммы:
    - Equipment "1" *-- "many" Sensor (композиция)
    - Equipment "1" *-- "many" MaintenanceRecord (композиция)
    """
    __tablename__ = "equipment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipment_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(100), nullable=False)
    status = Column(SQLEnum(EquipmentStatus), default=EquipmentStatus.ONLINE)
    installation_date = Column(Date, nullable=True)
    location = Column(String(200), nullable=True)
    description = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи - композиция (cascade delete)
    sensors = relationship("Sensor", back_populates="equipment", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceRecord", back_populates="equipment", cascade="all, delete-orphan")
    
    def get_current_metrics(self, db_session):
        """
        Получение текущих показателей со всех датчиков оборудования.
        Возвращает последние значения для каждого типа датчика.
        """
        metrics = {}
        for sensor in self.sensors:
            latest_data = (
                db_session.query(SensorData)
                .filter(SensorData.sensor_id == sensor.id)
                .order_by(SensorData.timestamp.desc())
                .first()
            )
            if latest_data:
                metrics[sensor.type.value] = {
                    "value": latest_data.value,
                    "unit": latest_data.unit,
                    "timestamp": latest_data.timestamp
                }
        return metrics
    
    def get_maintenance_history(self):
        """Получение истории обслуживания оборудования."""
        return sorted(self.maintenance_records, key=lambda r: r.date, reverse=True)


class Sensor(Base):
    """
    Датчик.
    
    Атрибуты из диаграммы:
    - sensorId: String - идентификатор
    - type: String - тип датчика
    - location: String - расположение
    - calibrationDate: Date - дата калибровки
    
    Методы из диаграммы:
    - readData() - чтение данных
    - validateData() - валидация данных
    
    Связи из диаграммы:
    - Sensor "1" *-- "many" SensorData (композиция)
    """
    __tablename__ = "sensors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(String(50), unique=True, nullable=False, index=True)
    type = Column(SQLEnum(SensorType), nullable=False)
    location = Column(String(200), nullable=True)
    calibration_date = Column(Date, nullable=True)
    
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    equipment = relationship("Equipment", back_populates="sensors")
    sensor_data = relationship("SensorData", back_populates="sensor", cascade="all, delete-orphan")
    
    def read_data(self, db_session, limit: int = 100):
        """Чтение последних данных с датчика."""
        return (
            db_session.query(SensorData)
            .filter(SensorData.sensor_id == self.id)
            .order_by(SensorData.timestamp.desc())
            .limit(limit)
            .all()
        )
    
    def validate_data(self, value: float) -> bool:
        """
        Проверка корректности значения датчика.
        Возвращает True если значение в допустимом диапазоне.
        """
        # Базовые диапазоны для разных типов датчиков
        ranges = {
            SensorType.TEMPERATURE: (-50, 200),
            SensorType.VIBRATION: (0, 50),
            SensorType.PRESSURE: (0, 1000),
            SensorType.CURRENT: (0, 100),
        }
        min_val, max_val = ranges.get(self.type, (0, float('inf')))
        return min_val <= value <= max_val


class SensorData(Base):
    """
    Данные датчика.
    
    Атрибуты из диаграммы:
    - dataId: String - идентификатор записи
    - timestamp: DateTime - временная метка
    - value: Double - значение
    - unit: String - единица измерения
    
    Методы из диаграммы:
    - validate() - валидация данных
    - formatForAnalysis() - форматирование для анализа
    """
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    data_id = Column(String(50), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    
    # Связи
    sensor = relationship("Sensor", back_populates="sensor_data")
    
    def validate(self) -> bool:
        """Проверка корректности записи данных."""
        if self.value is None or self.timestamp is None:
            return False
        return self.sensor.validate_data(self.value) if self.sensor else True
    
    def format_for_analysis(self) -> dict:
        """Форматирование данных для ML анализа."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "sensor_type": self.sensor.type.value if self.sensor else None,
            "equipment_id": self.sensor.equipment_id if self.sensor else None,
        }


class Alert(Base):
    """
    Оповещение о событии/аномалии.
    
    Дополнительная сущность для хранения событий системы.
    Не указана явно в диаграмме, но необходима для реализации
    функционала уведомлений из NotificationSubsystem.
    """
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(50), unique=True, nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    message = Column(String(500), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=True)
    
    is_read = Column(Integer, default=0)  # 0 - не прочитано, 1 - прочитано
    is_email_sent = Column(Integer, default=0)  # 0 - не отправлено, 1 - отправлено
    
    # Связи
    equipment = relationship("Equipment")
    sensor = relationship("Sensor")

