"""
Модель записи об обслуживании.
Реализация сущности MaintenanceRecord из UML диаграммы.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship

from database import Base


class MaintenanceRecord(Base):
    """
    Запись об обслуживании оборудования.
    
    Атрибуты из диаграммы:
    - recordId: String - идентификатор записи
    - date: Date - дата обслуживания
    - description: String - описание работ
    - technician: String - техник, выполнивший работу
    
    Методы из диаграммы:
    - addNote() - добавление заметки
    - markCompleted() - отметка о завершении
    """
    __tablename__ = "maintenance_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(String(50), unique=True, nullable=False, index=True)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    technician = Column(String(200), nullable=False)
    
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    
    # Дополнительные поля для расширенного функционала
    notes = Column(Text, nullable=True)
    is_completed = Column(Integer, default=0)  # 0 - в процессе, 1 - завершено
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    equipment = relationship("Equipment", back_populates="maintenance_records")
    
    def add_note(self, note: str):
        """
        Добавление заметки к записи об обслуживании.
        Накапливает заметки с отметкой времени.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        new_note = f"[{timestamp}] {note}"
        
        if self.notes:
            self.notes = f"{self.notes}\n{new_note}"
        else:
            self.notes = new_note
    
    def mark_completed(self):
        """Отметка записи как завершённой."""
        self.is_completed = 1
        self.completed_at = datetime.utcnow()

