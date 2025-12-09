"""
Модуль машинного обучения.
Содержит модели для прогнозирования отказов оборудования.
"""
from ml.models import MLModelManager
from ml.random_forest import RandomForestPredictor
from ml.lstm import LSTMPredictor

__all__ = [
    "MLModelManager",
    "RandomForestPredictor",
    "LSTMPredictor",
]

