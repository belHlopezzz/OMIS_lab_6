"""
Модель Random Forest для классификации состояния оборудования.
Определяет текущее состояние и вероятность отказа.
"""
import logging
from typing import Dict, List
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from ml.models import MLModelManager
from config import ML_MODELS_DIR


logger = logging.getLogger(__name__)


class RandomForestPredictor:
    """
    Предиктор на основе Random Forest.
    
    Классифицирует состояние оборудования:
    - 0: нормальное
    - 1: требует внимания
    - 2: критическое
    """
    
    MODEL_NAME = "random_forest_classifier"
    
    def __init__(self):
        self._model = None
        self._scaler = StandardScaler()
        self._manager = MLModelManager()
        self._feature_names = [
            "temp_current", "temp_mean", "temp_std",
            "vibr_current", "vibr_mean", "vibr_std",
            "press_current", "press_mean", "press_std",
            "curr_current", "curr_mean", "curr_std",
            "status_error",
        ]
        
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Загрузка существующей модели или создание новой."""
        if self._manager.model_exists(self.MODEL_NAME):
            self._model = self._manager.load_model(self.MODEL_NAME)
        else:
            self._create_and_train_initial_model()
    
    def _create_and_train_initial_model(self):
        """Создание и обучение модели на синтетических данных."""
        logger.info("Создание начальной модели Random Forest")
        
        # Генерируем синтетические обучающие данные
        X, y = self._generate_synthetic_data(n_samples=1000)
        
        # Обучаем модель
        self._model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1,
        )
        
        self._scaler.fit(X)
        X_scaled = self._scaler.transform(X)
        
        self._model.fit(X_scaled, y)
        
        # Сохраняем модель
        self._manager.save_model({
            "model": self._model,
            "scaler": self._scaler,
        }, self.MODEL_NAME)
        
        logger.info("Модель Random Forest обучена и сохранена")
    
    def _generate_synthetic_data(self, n_samples: int = 1000):
        """
        Генерация синтетических данных для обучения.
        Создаёт реалистичные паттерны нормального и аварийного состояния.
        """
        np.random.seed(42)
        
        X = []
        y = []
        
        for _ in range(n_samples):
            # Случайно выбираем класс
            label = np.random.choice([0, 1], p=[0.7, 0.3])
            
            if label == 0:  # Нормальное состояние
                features = [
                    np.random.normal(45, 5),   # temp_current
                    np.random.normal(45, 3),   # temp_mean
                    np.random.uniform(2, 5),   # temp_std
                    np.random.normal(2.5, 0.5),  # vibr_current
                    np.random.normal(2.5, 0.3),  # vibr_mean
                    np.random.uniform(0.3, 0.8), # vibr_std
                    np.random.normal(200, 20),   # press_current
                    np.random.normal(200, 15),   # press_mean
                    np.random.uniform(10, 20),   # press_std
                    np.random.normal(22, 3),     # curr_current
                    np.random.normal(22, 2),     # curr_mean
                    np.random.uniform(1, 3),     # curr_std
                    0,  # status_error
                ]
            else:  # Аварийное состояние
                features = [
                    np.random.normal(75, 10),    # temp_current - повышенная
                    np.random.normal(65, 8),     # temp_mean
                    np.random.uniform(8, 15),    # temp_std - высокая волатильность
                    np.random.normal(6, 1.5),    # vibr_current - повышенная
                    np.random.normal(5, 1),      # vibr_mean
                    np.random.uniform(1, 2.5),   # vibr_std
                    np.random.normal(350, 40),   # press_current - повышенное
                    np.random.normal(320, 30),   # press_mean
                    np.random.uniform(25, 40),   # press_std
                    np.random.normal(38, 5),     # curr_current - повышенный
                    np.random.normal(35, 4),     # curr_mean
                    np.random.uniform(3, 6),     # curr_std
                    np.random.choice([0, 1], p=[0.3, 0.7]),  # status_error
                ]
            
            X.append(features)
            y.append(label)
        
        return np.array(X), np.array(y)
    
    def _extract_feature_vector(self, features: Dict) -> np.ndarray:
        """Извлечение вектора признаков из словаря."""
        sensors = features.get("sensors", {})
        
        feature_vector = []
        
        for sensor_type in ["temperature", "vibration", "pressure", "current"]:
            sensor_data = sensors.get(sensor_type, {})
            feature_vector.extend([
                sensor_data.get("current", 0),
                sensor_data.get("mean", 0),
                sensor_data.get("std", 0),
            ])
        
        # Статус оборудования
        status_error = 1 if features.get("equipment_status") == "error" else 0
        feature_vector.append(status_error)
        
        return np.array(feature_vector).reshape(1, -1)
    
    def predict_probability(self, features: Dict) -> float:
        """
        Предсказание вероятности отказа.
        
        Returns:
            Вероятность отказа от 0 до 1
        """
        if self._model is None:
            return 0.5  # Возвращаем неопределённость если модель не загружена
        
        try:
            X = self._extract_feature_vector(features)
            X_scaled = self._scaler.transform(X)
            
            # Получаем вероятности классов
            probabilities = self._model.predict_proba(X_scaled)[0]
            
            # Возвращаем вероятность аварийного класса
            return float(probabilities[1]) if len(probabilities) > 1 else 0.5
            
        except Exception as e:
            logger.error(f"Ошибка предсказания: {e}")
            return 0.5
    
    def predict_class(self, features: Dict) -> int:
        """Предсказание класса состояния."""
        if self._model is None:
            return 0
        
        try:
            X = self._extract_feature_vector(features)
            X_scaled = self._scaler.transform(X)
            return int(self._model.predict(X_scaled)[0])
        except Exception as e:
            logger.error(f"Ошибка классификации: {e}")
            return 0
    
    def train(self, training_data: List[Dict]):
        """
        Дообучение модели на новых данных.
        
        Args:
            training_data: список словарей с features и label
        """
        if not training_data:
            return
        
        X = []
        y = []
        
        for sample in training_data:
            features = sample.get("features", {})
            label = sample.get("label", 0)
            
            X.append(self._extract_feature_vector(features).flatten())
            y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        if len(X) < 10:
            logger.warning("Недостаточно данных для обучения")
            return
        
        X_scaled = self._scaler.fit_transform(X)
        self._model.fit(X_scaled, y)
        
        self._manager.save_model({
            "model": self._model,
            "scaler": self._scaler,
        }, self.MODEL_NAME)
        
        logger.info(f"Модель дообучена на {len(X)} образцах")

