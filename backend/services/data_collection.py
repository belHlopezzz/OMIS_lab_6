"""
Подсистема сбора данных (DataCollectionSubsystem).
Реализация интерфейса DataCollector из UML диаграммы.

Примечание к диаграмме: вместо MQTT/HTTP клиентов используются моки для симуляции
данных датчиков, так как реальные IoT устройства недоступны.
Данные сохраняются в SQLite вместо PostgreSQL согласно требованиям.
"""
import asyncio
import uuid
import random
import logging
from datetime import datetime
from abc import ABC, abstractmethod

from database import SessionLocal
from models.equipment import Equipment, Sensor, SensorData, SensorType, Alert, AlertSeverity, EquipmentStatus
from config import SENSOR_THRESHOLDS, DATA_GENERATION_INTERVAL


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCollector(ABC):
    """
    Интерфейс DataCollector из UML диаграммы.
    Определяет методы для сбора, фильтрации и хранения данных.
    """
    
    @abstractmethod
    def collect_data(self):
        """Сбор данных с датчиков."""
        pass
    
    @abstractmethod
    def filter_data(self, value: float, sensor_type: SensorType) -> float:
        """Фильтрация шумов в данных."""
        pass
    
    @abstractmethod
    def store_data(self, sensor_id: int, value: float, unit: str):
        """Сохранение данных в базу."""
        pass


class DataCollectionSubsystem(DataCollector):
    """
    Реализация подсистемы сбора данных.
    
    Примечание к диаграмме: атрибуты mqttClient и httpClient заменены на
    генератор синтетических данных, так как реальные датчики недоступны.
    
    Методы из диаграммы:
    - receiveSensorData() - получение данных (симуляция)
    - aggregateData() - агрегация данных
    - removeNoise() - удаление шумов
    """
    
    def __init__(self):
        # Вместо MQTT/HTTP клиентов используем параметры генерации
        self._noise_filter_window = 5  # окно для скользящего среднего
        self._recent_values = {}  # кэш последних значений для фильтрации
        
        # Базовые параметры генерации для каждого типа датчика
        self._generation_params = {
            SensorType.TEMPERATURE: {"base": 45, "variance": 10, "drift": 0.5},
            SensorType.VIBRATION: {"base": 2.5, "variance": 1.0, "drift": 0.2},
            SensorType.PRESSURE: {"base": 200, "variance": 30, "drift": 1.0},
            SensorType.CURRENT: {"base": 22, "variance": 5, "drift": 0.3},
        }
    
    async def start_data_collection(self):
        """
        Запуск периодического сбора данных.
        Работает как фоновая задача asyncio.
        """
        logger.info("Запуск подсистемы сбора данных")
        
        while True:
            try:
                await self._collection_cycle()
            except Exception as e:
                logger.error(f"Ошибка в цикле сбора данных: {e}")
            
            await asyncio.sleep(DATA_GENERATION_INTERVAL)
    
    async def _collection_cycle(self):
        """Один цикл сбора данных для всех датчиков."""
        db = SessionLocal()
        
        try:
            sensors = db.query(Sensor).all()
            
            for sensor in sensors:
                # Симулируем получение данных
                raw_value = self.receive_sensor_data(sensor)
                
                # Фильтруем шумы
                filtered_value = self.filter_data(raw_value, sensor.type)
                
                # Валидируем данные
                if sensor.validate_data(filtered_value):
                    # Сохраняем в базу
                    self.store_data(db, sensor.id, filtered_value, self._get_unit(sensor.type))
                    
                    # Проверяем пороги и создаём оповещения
                    self._check_thresholds(db, sensor, filtered_value)
            
            db.commit()
            logger.debug(f"Цикл сбора данных завершён, обработано {len(sensors)} датчиков")
            
        finally:
            db.close()
    
    def receive_sensor_data(self, sensor: Sensor) -> float:
        """
        Симуляция получения данных с датчика.
        Реализация метода receiveSensorData() из диаграммы.
        
        Генерирует реалистичные значения с учётом:
        - базового уровня для типа датчика
        - случайного шума
        - временного дрифта
        - периодических аномалий
        """
        params = self._generation_params[sensor.type]
        
        # Базовое значение с нормальным шумом
        value = params["base"] + random.gauss(0, params["variance"])
        
        # Временной дрифт (медленное изменение)
        hour = datetime.utcnow().hour
        value += params["drift"] * (hour - 12) / 12
        
        # Суточный цикл для температуры
        if sensor.type == SensorType.TEMPERATURE:
            value += 3 * (1 - abs(hour - 14) / 12)
        
        # Случайные аномалии (увеличиваем до 50% для демонстрации)
        if random.random() < 0.5:
            # Всплеск или падение
            value += random.choice([-1, 1]) * params["variance"] * random.uniform(1.5, 4)
        
        # Проверяем статус оборудования - проблемное генерирует больше аномалий
        equipment = sensor.equipment
        if equipment and equipment.status == EquipmentStatus.ERROR:
            if random.random() < 0.8:  # 80% шанс аномалии для проблемного оборудования
                value += params["variance"] * random.uniform(2.5, 5)
        
        # Дополнительно: форсируем выход за порог для демонстрации (высокая вероятность)
        if random.random() < 0.5:  # 50% шанс форсировать порог
            sensor_thresholds = SENSOR_THRESHOLDS.get(sensor.type.value, {})
            warning_threshold = sensor_thresholds.get("warning", 0)
            critical_threshold = sensor_thresholds.get("critical", warning_threshold * 1.2)
            if critical_threshold > 0:
                # 70% шанс попасть в критический диапазон, 30% — в предупреждение
                if random.random() < 0.7:
                    # Критическое значение - превышаем порог на 5-15%
                    value = critical_threshold + random.uniform(
                        critical_threshold * 0.05, 
                        critical_threshold * 0.15
                    )
                else:
                    # Предупреждение - близко к критическому порогу
                    value = warning_threshold + random.uniform(
                        warning_threshold * 0.1, 
                        warning_threshold * 0.3
                    )
        
        return max(0, value)  # значения не могут быть отрицательными
    
    def collect_data(self):
        """Реализация метода интерфейса - вызывается из цикла."""
        pass  # Логика реализована в _collection_cycle
    
    def filter_data(self, value: float, sensor_type: SensorType) -> float:
        """
        Фильтрация шумов методом скользящего среднего.
        Реализация метода removeNoise() из диаграммы.
        """
        key = sensor_type.value
        
        if key not in self._recent_values:
            self._recent_values[key] = []
        
        self._recent_values[key].append(value)
        
        # Сохраняем только последние N значений
        if len(self._recent_values[key]) > self._noise_filter_window:
            self._recent_values[key].pop(0)
        
        # Возвращаем среднее для сглаживания
        return round(sum(self._recent_values[key]) / len(self._recent_values[key]), 2)
    
    def store_data(self, db, sensor_id: int, value: float, unit: str):
        """
        Сохранение данных в базу.
        Реализация метода storeData() из интерфейса DataCollector.
        """
        sensor_data = SensorData(
            data_id=f"DAT-{str(uuid.uuid4())[:8]}",
            timestamp=datetime.utcnow(),
            value=value,
            unit=unit,
            sensor_id=sensor_id,
        )
        db.add(sensor_data)
    
    def aggregate_data(self, db, sensor_id: int, hours: int = 1) -> dict:
        """
        Агрегация данных за период.
        Реализация метода aggregateData() из диаграммы.
        """
        from datetime import timedelta
        from sqlalchemy import func
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        result = db.query(
            func.avg(SensorData.value).label("avg"),
            func.min(SensorData.value).label("min"),
            func.max(SensorData.value).label("max"),
            func.count(SensorData.id).label("count"),
        ).filter(
            SensorData.sensor_id == sensor_id,
            SensorData.timestamp >= start_time,
            SensorData.timestamp <= end_time,
        ).first()
        
        return {
            "avg": round(result.avg, 2) if result.avg else 0,
            "min": round(result.min, 2) if result.min else 0,
            "max": round(result.max, 2) if result.max else 0,
            "count": result.count,
        }
    
    def _check_thresholds(self, db, sensor: Sensor, value: float):
        """
        Проверка пороговых значений и создание оповещений.
        Предотвращает создание дубликатов слишком часто (не чаще раза в 5 минут).
        """
        from datetime import timedelta
        
        thresholds = SENSOR_THRESHOLDS.get(sensor.type.value)
        
        if not thresholds:
            return
        
        equipment = sensor.equipment
        severity = None
        message = None
        
        if value >= thresholds["critical"]:
            severity = AlertSeverity.CRITICAL
            message = f"Критическое значение {sensor.type.value}: {value:.2f} {thresholds['unit']}"
            
            # Обновляем статус оборудования
            if equipment:
                equipment.status = EquipmentStatus.ERROR
                
        elif value >= thresholds["warning"]:
            severity = AlertSeverity.WARNING
            message = f"Превышен порог {sensor.type.value}: {value:.2f} {thresholds['unit']}"
        
        if severity and equipment:
            # Проверяем, не создавали ли мы недавно оповещение для этого датчика
            # (чтобы не спамить одинаковыми событиями)
            recent_time = datetime.utcnow() - timedelta(minutes=5)
            recent_alert = (
                db.query(Alert)
                .filter(
                    Alert.sensor_id == sensor.id,
                    Alert.severity == severity,
                    Alert.timestamp >= recent_time
                )
                .first()
            )
            
            # Создаём оповещение только если не было недавно такого же
            if not recent_alert:
                alert = Alert(
                    alert_id=f"ALR-{str(uuid.uuid4())[:8]}",
                    severity=severity,
                    message=message,
                    equipment_id=equipment.id,
                    sensor_id=sensor.id,
                )
                db.add(alert)
                db.flush()  # Сохраняем чтобы получить ID
                logger.warning(f"Создано оповещение: {message}")
                
                # Отправляем email для критических событий
                if severity == AlertSeverity.CRITICAL:
                    try:
                        from services.notifications import NotificationSubsystem
                        notifier = NotificationSubsystem()
                        notifier.notify_critical_alert(db, alert)
                        logger.info(f"Email отправлен для критического события: {alert.alert_id}")
                    except Exception as e:
                        logger.error(f"Ошибка отправки email: {e}")
    
    def _get_unit(self, sensor_type: SensorType) -> str:
        """Получение единицы измерения для типа датчика."""
        units = {
            SensorType.TEMPERATURE: "°C",
            SensorType.VIBRATION: "мм/с",
            SensorType.PRESSURE: "кПа",
            SensorType.CURRENT: "А",
        }
        return units.get(sensor_type, "")

