"""
Менеджер ML моделей.
Управляет загрузкой, сохранением и использованием моделей.
"""
import os
import pickle
import logging
from pathlib import Path

from config import ML_MODELS_DIR


logger = logging.getLogger(__name__)


class MLModelManager:
    """
    Менеджер моделей машинного обучения.
    Обеспечивает единый интерфейс для работы с моделями.
    """
    
    def __init__(self):
        self.models_dir = ML_MODELS_DIR
        self._models = {}
    
    def save_model(self, model, name: str):
        """Сохранение модели на диск."""
        path = self.models_dir / f"{name}.pkl"
        
        try:
            with open(path, "wb") as f:
                pickle.dump(model, f)
            logger.info(f"Модель {name} сохранена: {path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения модели {name}: {e}")
    
    def load_model(self, name: str):
        """Загрузка модели с диска."""
        path = self.models_dir / f"{name}.pkl"
        
        if not path.exists():
            logger.warning(f"Модель {name} не найдена: {path}")
            return None
        
        try:
            with open(path, "rb") as f:
                model = pickle.load(f)
            logger.info(f"Модель {name} загружена")
            return model
        except Exception as e:
            logger.error(f"Ошибка загрузки модели {name}: {e}")
            return None
    
    def get_model(self, name: str):
        """Получение модели из кэша или загрузка."""
        if name not in self._models:
            self._models[name] = self.load_model(name)
        return self._models[name]
    
    def model_exists(self, name: str) -> bool:
        """Проверка существования модели."""
        path = self.models_dir / f"{name}.pkl"
        return path.exists()

