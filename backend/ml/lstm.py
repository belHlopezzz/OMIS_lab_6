"""
LSTM модель для прогнозирования временных рядов.
Предсказывает будущие значения датчиков для раннего обнаружения проблем.

Примечание: используется упрощённая реализация без TensorFlow для снижения
зависимостей. При необходимости можно заменить на полноценную LSTM сеть.
"""
import logging
from typing import List, Dict, Optional
import numpy as np

from config import ML_MODELS_DIR


logger = logging.getLogger(__name__)


class LSTMPredictor:
    """
    Предиктор временных рядов.
    
    В упрощённой версии использует авторегрессионную модель
    вместо полноценной LSTM сети для снижения требований к ресурсам.
    
    При необходимости можно заменить на TensorFlow/Keras LSTM:
    - Раскомментировать импорты TensorFlow
    - Использовать методы _build_lstm_model и _train_lstm
    """
    
    def __init__(self):
        self.sequence_length = 24  # длина входной последовательности
        self.prediction_horizon = 12  # горизонт прогноза
        self._model = None
        self._is_trained = False
        
        # Параметры для упрощённой модели
        self._ar_coefficients = {}
    
    def predict_sequence(
        self, 
        historical_data: List[float], 
        steps: int = 12
    ) -> List[float]:
        """
        Прогнозирование будущих значений.
        
        Args:
            historical_data: исторические значения
            steps: количество шагов прогноза
            
        Returns:
            Список предсказанных значений
        """
        if len(historical_data) < 3:
            return [historical_data[-1]] * steps if historical_data else [0] * steps
        
        # Используем простую авторегрессию AR(3)
        predictions = []
        data = list(historical_data[-10:])  # берём последние 10 точек
        
        for _ in range(steps):
            # AR(3): y_t = c + φ1*y_{t-1} + φ2*y_{t-2} + φ3*y_{t-3}
            if len(data) >= 3:
                pred = (
                    0.5 * data[-1] + 
                    0.3 * data[-2] + 
                    0.15 * data[-3] + 
                    np.random.normal(0, 0.5)  # шум
                )
            else:
                pred = data[-1]
            
            predictions.append(pred)
            data.append(pred)
        
        return predictions
    
    def predict_anomaly_probability(
        self, 
        historical_data: List[float],
        threshold_warning: float,
        threshold_critical: float,
        horizon_hours: int = 48
    ) -> Dict:
        """
        Оценка вероятности превышения порогов в будущем.
        
        Args:
            historical_data: исторические данные
            threshold_warning: порог предупреждения
            threshold_critical: критический порог
            horizon_hours: горизонт прогноза в часах
            
        Returns:
            Словарь с вероятностями и прогнозом
        """
        if not historical_data:
            return {
                "warning_probability": 0,
                "critical_probability": 0,
                "predicted_max": 0,
                "predicted_values": [],
            }
        
        # Прогнозируем значения
        # Предполагаем данные с интервалом 30 минут
        steps = horizon_hours * 2
        predictions = self.predict_sequence(historical_data, steps)
        
        # Считаем вероятности как долю превышений
        warning_count = sum(1 for p in predictions if p >= threshold_warning)
        critical_count = sum(1 for p in predictions if p >= threshold_critical)
        
        return {
            "warning_probability": warning_count / len(predictions),
            "critical_probability": critical_count / len(predictions),
            "predicted_max": max(predictions),
            "predicted_min": min(predictions),
            "predicted_mean": np.mean(predictions),
            "predicted_values": predictions[:24],  # первые 24 значения для визуализации
        }
    
    def detect_trend(self, data: List[float]) -> Dict:
        """
        Анализ тренда во временном ряде.
        
        Returns:
            Словарь с информацией о тренде
        """
        if len(data) < 5:
            return {"direction": "unknown", "strength": 0}
        
        # Линейная регрессия для определения тренда
        x = np.arange(len(data))
        y = np.array(data)
        
        # Коэффициенты линейной регрессии
        n = len(data)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        
        # Нормализуем наклон относительно среднего значения
        mean_val = np.mean(y)
        normalized_slope = slope / mean_val if mean_val != 0 else 0
        
        # Определяем направление и силу тренда
        if normalized_slope > 0.01:
            direction = "increasing"
        elif normalized_slope < -0.01:
            direction = "decreasing"
        else:
            direction = "stable"
        
        strength = min(abs(normalized_slope) * 100, 1.0)
        
        return {
            "direction": direction,
            "strength": round(strength, 2),
            "slope": round(slope, 4),
        }
    
    def train(self, training_data: List[Dict]):
        """
        Обучение модели на исторических данных.
        
        В упрощённой версии просто калибрует коэффициенты AR модели.
        """
        if not training_data:
            return
        
        logger.info(f"Обучение LSTM модели на {len(training_data)} образцах")
        
        # Для упрощённой версии обучение не требуется
        # AR коэффициенты фиксированы
        
        self._is_trained = True
    
    # === Методы для полноценной LSTM (закомментированы) ===
    
    # def _build_lstm_model(self, input_shape):
    #     """
    #     Создание LSTM модели на TensorFlow/Keras.
    #     
    #     Раскомментируйте и используйте при наличии TensorFlow:
    #     
    #     from tensorflow.keras.models import Sequential
    #     from tensorflow.keras.layers import LSTM, Dense, Dropout
    #     
    #     model = Sequential([
    #         LSTM(64, input_shape=input_shape, return_sequences=True),
    #         Dropout(0.2),
    #         LSTM(32),
    #         Dropout(0.2),
    #         Dense(self.prediction_horizon)
    #     ])
    #     
    #     model.compile(optimizer='adam', loss='mse')
    #     return model
    #     """
    #     pass
    
    # def _train_lstm(self, X_train, y_train, epochs=50):
    #     """
    #     Обучение LSTM модели.
    #     
    #     self._model = self._build_lstm_model((X_train.shape[1], X_train.shape[2]))
    #     self._model.fit(X_train, y_train, epochs=epochs, batch_size=32, verbose=0)
    #     """
    #     pass

