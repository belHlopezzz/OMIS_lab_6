"""
Роутер датчиков и данных.
Реализует методы из классов Sensor и SensorData.
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.equipment import Sensor, SensorData, SensorType, Equipment
from schemas.equipment import SensorCreate, SensorResponse, SensorDataResponse
from utils.dependencies import get_current_user, get_admin_user, get_operator_user


router = APIRouter()


@router.get("/{equipment_id}/data")
async def get_sensor_data(
    equipment_id: int,
    sensor_type: Optional[str] = Query(None, description="Тип датчика"),
    hours: int = Query(24, description="Период в часах"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение данных датчиков для оборудования.
    Реализация метода readData() из класса Sensor.
    """
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    # Фильтруем датчики
    sensors_query = db.query(Sensor).filter(Sensor.equipment_id == equipment_id)
    
    if sensor_type:
        try:
            type_enum = SensorType(sensor_type)
            sensors_query = sensors_query.filter(Sensor.type == type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неверный тип датчика: {sensor_type}"
            )
    
    sensors = sensors_query.all()
    
    # Временные границы
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    result = {}
    
    for sensor in sensors:
        data = (
            db.query(SensorData)
            .filter(
                SensorData.sensor_id == sensor.id,
                SensorData.timestamp >= start_time,
                SensorData.timestamp <= end_time
            )
            .order_by(SensorData.timestamp.asc())
            .all()
        )
        
        result[sensor.type.value] = {
            "sensor_id": sensor.sensor_id,
            "data": [
                {
                    "timestamp": d.timestamp.isoformat(),
                    "value": d.value,
                    "unit": d.unit,
                }
                for d in data
            ]
        }
    
    return result


@router.post("/{equipment_id}/data")
async def add_sensor_data(
    equipment_id: int,
    sensor_type: str,
    value: float,
    current_user: User = Depends(get_operator_user),
    db: Session = Depends(get_db)
):
    """
    Ручной ввод данных датчика.
    Реализация метода inputSensorData() из класса Operator.
    
    Примечание к диаграмме: в реальной системе данные собираются автоматически,
    но оператор может вводить данные вручную при необходимости.
    """
    # Находим датчик
    try:
        type_enum = SensorType(sensor_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный тип датчика: {sensor_type}"
        )
    
    sensor = db.query(Sensor).filter(
        Sensor.equipment_id == equipment_id,
        Sensor.type == type_enum
    ).first()
    
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Датчик не найден"
        )
    
    # Валидируем данные
    if not sensor.validate_data(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Значение вне допустимого диапазона"
        )
    
    # Определяем единицу измерения
    units = {
        SensorType.TEMPERATURE: "°C",
        SensorType.VIBRATION: "мм/с",
        SensorType.PRESSURE: "кПа",
        SensorType.CURRENT: "А",
    }
    
    # Создаём запись
    new_data = SensorData(
        data_id=f"DAT-{str(uuid.uuid4())[:8]}",
        timestamp=datetime.utcnow(),
        value=value,
        unit=units[type_enum],
        sensor_id=sensor.id,
    )
    
    db.add(new_data)
    db.commit()
    
    return {
        "message": "Данные добавлены",
        "data_id": new_data.data_id,
        "timestamp": new_data.timestamp.isoformat(),
    }


@router.post("/{equipment_id}/sensors", status_code=status.HTTP_201_CREATED)
async def create_sensor(
    equipment_id: int,
    sensor_data: SensorCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Добавление нового датчика к оборудованию.
    Часть метода configureSystem() из класса Administrator.
    """
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    # Проверяем, нет ли уже датчика такого типа
    existing = db.query(Sensor).filter(
        Sensor.equipment_id == equipment_id,
        Sensor.type == sensor_data.type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Датчик типа {sensor_data.type.value} уже существует"
        )
    
    new_sensor = Sensor(
        sensor_id=f"SNS-{str(uuid.uuid4())[:8]}",
        type=sensor_data.type,
        location=sensor_data.location or f"{eq.location}, {eq.name}",
        calibration_date=sensor_data.calibration_date,
        equipment_id=equipment_id,
    )
    
    db.add(new_sensor)
    db.commit()
    db.refresh(new_sensor)
    
    return {
        "message": "Датчик создан",
        "sensor_id": new_sensor.sensor_id,
        "type": new_sensor.type.value,
    }


@router.get("/{equipment_id}/latest")
async def get_latest_readings(
    equipment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение последних показаний всех датчиков оборудования."""
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    result = {}
    
    for sensor in eq.sensors:
        latest = (
            db.query(SensorData)
            .filter(SensorData.sensor_id == sensor.id)
            .order_by(SensorData.timestamp.desc())
            .first()
        )
        
        if latest:
            result[sensor.type.value] = {
                "value": latest.value,
                "unit": latest.unit,
                "timestamp": latest.timestamp.isoformat(),
                "sensor_id": sensor.sensor_id,
            }
    
    return result

