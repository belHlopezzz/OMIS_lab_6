"""
Подсистема анализа и прогнозирования (AnalysisSubsystem).
Реализация интерфейса Analyzer из UML диаграммы.

Использует ML алгоритмы для прогнозирования отказов:
- Random Forest для классификации состояния
- LSTM для временных рядов (упрощённая версия)
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from sqlalchemy.orm import Session
import numpy as np

from models.equipment import Equipment, Sensor, SensorData, SensorType, EquipmentStatus
from schemas.prediction import FailurePrediction
from config import SENSOR_THRESHOLDS, ML_PREDICTION_HORIZON_HOURS, ANOMALY_PROBABILITY_THRESHOLD


logger = logging.getLogger(__name__)


class Analyzer(ABC):
    """
    Интерфейс Analyzer из UML диаграммы.
    Определяет методы для анализа данных и прогнозирования.
    """
    
    @abstractmethod
    def analyze_data(self, data: List[Dict]) -> Dict:
        """Анализ данных датчиков."""
        pass
    
    @abstractmethod
    def detect_anomalies(self, db: Session, equipment_id: int) -> List[Dict]:
        """Обнаружение аномалий."""
        pass
    
    @abstractmethod
    def predict_failures(self, db: Session, equipment_id: int) -> Dict:
        """Прогнозирование отказов."""
        pass


class AnalysisSubsystem(Analyzer):
    """
    Реализация подсистемы анализа.
    
    Атрибуты из диаграммы:
    - mlModel: MLModel - модели машинного обучения
    - threshold: Double - пороговые значения
    
    Методы из диаграммы:
    - processData() - обработка данных
    - trainModel() - обучение модели
    - generatePredictions() - генерация прогнозов
    """
    
    def __init__(self):
        self.threshold = ANOMALY_PROBABILITY_THRESHOLD
        self._rf_model = None
        self._lstm_model = None
        self._models_loaded = False
        
        # Загружаем или инициализируем модели
        self._initialize_models()
    
    def _initialize_models(self):
        """Инициализация ML моделей."""
        try:
            from ml.random_forest import RandomForestPredictor
            from ml.lstm import LSTMPredictor
            
            self._rf_model = RandomForestPredictor()
            self._lstm_model = LSTMPredictor()
            self._models_loaded = True
            logger.info("ML модели инициализированы")
        except Exception as e:
            logger.warning(f"Не удалось загрузить ML модели: {e}")
            self._models_loaded = False
    
    def analyze_data(self, data: List[Dict]) -> Dict:
        """
        Анализ данных датчиков.
        Вычисляет статистики и выявляет тренды.
        """
        if not data:
            return {"status": "no_data"}
        
        values = [d["value"] for d in data if "value" in d]
        
        if not values:
            return {"status": "no_values"}
        
        return {
            "count": len(values),
            "mean": np.mean(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "trend": self._calculate_trend(values),
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Определение тренда по последним значениям."""
        if len(values) < 3:
            return "stable"
        
        # Сравниваем среднее первой и последней трети
        third = len(values) // 3
        first_avg = np.mean(values[:third])
        last_avg = np.mean(values[-third:])
        
        diff_percent = (last_avg - first_avg) / first_avg * 100 if first_avg != 0 else 0
        
        if diff_percent > 10:
            return "increasing"
        elif diff_percent < -10:
            return "decreasing"
        return "stable"
    
    def detect_anomalies(self, db: Session, equipment_id: int) -> List[Dict]:
        """
        Обнаружение аномалий в данных оборудования.
        Реализация метода detectAnomalies() из интерфейса Analyzer.
        """
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        
        if not equipment:
            return []
        
        anomalies = []
        
        for sensor in equipment.sensors:
            # Получаем последние данные
            recent_data = (
                db.query(SensorData)
                .filter(SensorData.sensor_id == sensor.id)
                .order_by(SensorData.timestamp.desc())
                .limit(100)
                .all()
            )
            
            if not recent_data:
                continue
            
            values = [d.value for d in recent_data]
            current_value = values[0]
            
            # Статистический анализ
            mean = np.mean(values)
            std = np.std(values)
            
            # Z-score для текущего значения
            z_score = abs(current_value - mean) / std if std > 0 else 0
            
            # Проверяем пороги
            thresholds = SENSOR_THRESHOLDS.get(sensor.type.value, {})
            warning_threshold = thresholds.get("warning", float("inf"))
            critical_threshold = thresholds.get("critical", float("inf"))
            
            is_anomaly = z_score > 2 or current_value >= warning_threshold
            
            anomaly_result = {
                "sensor_type": sensor.type.value,
                "is_anomaly": is_anomaly,
                "anomaly_score": round(z_score, 2),
                "current_value": current_value,
                "expected_range": (round(mean - 2*std, 2), round(mean + 2*std, 2)),
                "message": None,
            }
            
            if current_value >= critical_threshold:
                anomaly_result["message"] = f"Критическое значение: {current_value}"
            elif current_value >= warning_threshold:
                anomaly_result["message"] = f"Превышен порог предупреждения: {current_value}"
            elif z_score > 3:
                anomaly_result["message"] = f"Статистическая аномалия (z={z_score:.1f})"
            
            anomalies.append(anomaly_result)
        
        return anomalies
    
    def predict_failures(self, db: Session, equipment_id: int) -> Dict:
        """
        Прогнозирование отказов оборудования.
        Реализация метода predictFailures() из интерфейса Analyzer.
        """
        return self.predict_failure(db, equipment_id, ML_PREDICTION_HORIZON_HOURS)
    
    def predict_failure(self, db: Session, equipment_id: int, horizon_hours: int = 48) -> Dict:
        """
        Генерация прогноза отказа.
        Реализация метода generatePredictions() из диаграммы.
        """
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        
        if not equipment:
            raise ValueError(f"Оборудование {equipment_id} не найдено")
        
        # Собираем данные для анализа
        features = self._extract_features(db, equipment)
        
        # Используем ML модель если доступна
        if self._models_loaded and self._rf_model:
            try:
                probability = self._rf_model.predict_probability(features)
            except Exception as e:
                logger.warning(f"Ошибка RF модели: {e}")
                probability = self._heuristic_prediction(features)
        else:
            probability = self._heuristic_prediction(features)
        
        # Определяем уровень риска
        risk_level = self._get_risk_level(probability)
        
        # Формируем факторы риска
        factors = self._identify_risk_factors(features)
        
        # Генерируем рекомендации
        recommendations = self._generate_recommendations(risk_level, factors, equipment)
        
        prediction = FailurePrediction(
            probability=round(probability, 2),
            confidence=0.75 if self._models_loaded else 0.5,
            time_window_hours=horizon_hours,
            risk_level=risk_level,
            factors=factors,
        )
        
        return {
            "prediction": prediction,
            "recommendations": recommendations,
        }
    
    def _extract_features(self, db: Session, equipment: Equipment) -> Dict:
        """Извлечение признаков для ML модели."""
        features = {
            "equipment_status": equipment.status.value,
            "sensors": {},
        }
        
        for sensor in equipment.sensors:
            # Последние данные за 24 часа
            cutoff = datetime.utcnow() - timedelta(hours=24)
            data = (
                db.query(SensorData)
                .filter(
                    SensorData.sensor_id == sensor.id,
                    SensorData.timestamp >= cutoff
                )
                .order_by(SensorData.timestamp.desc())
                .all()
            )
            
            if data:
                values = [d.value for d in data]
                features["sensors"][sensor.type.value] = {
                    "current": values[0],
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "max": np.max(values),
                    "min": np.min(values),
                    "trend": self._calculate_trend(values),
                }
        
        return features
    
    def _heuristic_prediction(self, features: Dict) -> float:
        """
        Эвристический прогноз на основе правил.
        Используется если ML модели недоступны.
        """
        probability = 0.1  # базовая вероятность
        
        # Учитываем текущий статус
        if features["equipment_status"] == "error":
            probability += 0.4
        elif features["equipment_status"] == "offline":
            probability += 0.2
        
        # Анализируем показания датчиков
        for sensor_type, sensor_data in features.get("sensors", {}).items():
            thresholds = SENSOR_THRESHOLDS.get(sensor_type, {})
            
            if not thresholds:
                continue
            
            current = sensor_data.get("current", 0)
            warning = thresholds.get("warning", float("inf"))
            critical = thresholds.get("critical", float("inf"))
            
            if current >= critical:
                probability += 0.3
            elif current >= warning:
                probability += 0.15
            
            # Учитываем тренд
            if sensor_data.get("trend") == "increasing":
                probability += 0.05
        
        return min(probability, 0.99)
    
    def _get_risk_level(self, probability: float) -> str:
        """Определение уровня риска по вероятности."""
        if probability >= 0.8:
            return "critical"
        elif probability >= 0.6:
            return "high"
        elif probability >= 0.3:
            return "medium"
        return "low"
    
    def _identify_risk_factors(self, features: Dict) -> List[str]:
        """Определение факторов риска."""
        factors = []
        
        if features["equipment_status"] == "error":
            factors.append("Оборудование в аварийном состоянии")
        
        for sensor_type, sensor_data in features.get("sensors", {}).items():
            thresholds = SENSOR_THRESHOLDS.get(sensor_type, {})
            
            if not thresholds:
                continue
            
            current = sensor_data.get("current", 0)
            warning = thresholds.get("warning", float("inf"))
            
            if current >= warning:
                sensor_names = {
                    "temperature": "температура",
                    "vibration": "вибрация", 
                    "pressure": "давление",
                    "current": "ток",
                }
                factors.append(f"Повышенная {sensor_names.get(sensor_type, sensor_type)}")
            
            if sensor_data.get("trend") == "increasing":
                factors.append(f"Растущий тренд: {sensor_type}")
        
        return factors if factors else ["Факторы риска не выявлены"]
    
    def _generate_recommendations(
        self, 
        risk_level: str, 
        factors: List[str],
        equipment: Equipment
    ) -> List[str]:
        """Генерация рекомендаций по обслуживанию."""
        recommendations = []
        
        if risk_level == "critical":
            recommendations.append(f"Немедленно остановить {equipment.name} для диагностики")
            recommendations.append("Вызвать техническую бригаду")
        elif risk_level == "high":
            recommendations.append(f"Запланировать срочное обслуживание {equipment.name}")
            recommendations.append("Усилить мониторинг показателей")
        elif risk_level == "medium":
            recommendations.append("Провести профилактический осмотр")
            recommendations.append("Проверить калибровку датчиков")
        else:
            recommendations.append("Продолжать штатный мониторинг")
        
        # Специфичные рекомендации по факторам
        for factor in factors:
            if "температура" in factor.lower():
                recommendations.append("Проверить систему охлаждения")
            elif "вибрация" in factor.lower():
                recommendations.append("Проверить балансировку и крепления")
            elif "давление" in factor.lower():
                recommendations.append("Проверить герметичность системы")
        
        return recommendations
    
    def process_data(self, db: Session, equipment_id: int):
        """
        Обработка данных оборудования.
        Реализация метода processData() из диаграммы.
        """
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        
        if not equipment:
            return None
        
        results = {}
        
        for sensor in equipment.sensors:
            data = (
                db.query(SensorData)
                .filter(SensorData.sensor_id == sensor.id)
                .order_by(SensorData.timestamp.desc())
                .limit(100)
                .all()
            )
            
            formatted_data = [d.format_for_analysis() for d in data]
            results[sensor.type.value] = self.analyze_data(formatted_data)
        
        return results
    
    def train_model(self, db: Session):
        """
        Обучение ML модели на исторических данных.
        Реализация метода trainModel() из диаграммы.
        """
        if self._rf_model:
            # Собираем обучающие данные
            training_data = self._collect_training_data(db)
            self._rf_model.train(training_data)
            logger.info("Модель Random Forest обучена")
    
    def _collect_training_data(self, db: Session) -> List[Dict]:
        """Сбор данных для обучения модели."""
        training_samples = []
        
        equipment_list = db.query(Equipment).all()
        
        for equipment in equipment_list:
            features = self._extract_features(db, equipment)
            
            # Определяем целевую переменную на основе статуса
            label = 1 if equipment.status == EquipmentStatus.ERROR else 0
            
            training_samples.append({
                "features": features,
                "label": label,
            })
        
        return training_samples

