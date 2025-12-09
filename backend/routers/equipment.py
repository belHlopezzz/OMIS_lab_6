"""
Роутер оборудования.
Реализует методы из классов Equipment, Operator и Administrator.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, UserRole
from models.equipment import Equipment, EquipmentStatus, Sensor, SensorData
from models.maintenance import MaintenanceRecord
from schemas.equipment import (
    EquipmentCreate, EquipmentResponse, EquipmentWithMetrics
)
from schemas.maintenance import MaintenanceRecordResponse
from utils.dependencies import get_current_user, get_admin_user, get_operator_user


router = APIRouter()


@router.get("", response_model=List[EquipmentWithMetrics])
async def get_equipment_list(
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка оборудования.
    Реализация метода monitorEquipment() из класса Operator.
    """
    query = db.query(Equipment)
    
    if status_filter and status_filter != "all":
        try:
            status_enum = EquipmentStatus(status_filter)
            query = query.filter(Equipment.status == status_enum)
        except ValueError:
            pass
    
    equipment_list = query.all()
    result = []
    
    for eq in equipment_list:
        # Получаем последнее обновление данных
        latest_data = None
        metrics = {}
        
        for sensor in eq.sensors:
            last_reading = (
                db.query(SensorData)
                .filter(SensorData.sensor_id == sensor.id)
                .order_by(SensorData.timestamp.desc())
                .first()
            )
            
            if last_reading:
                if latest_data is None or last_reading.timestamp > latest_data:
                    latest_data = last_reading.timestamp
                
                metrics[sensor.type.value] = {
                    "value": last_reading.value,
                    "unit": last_reading.unit,
                }
        
        # Формируем данные о датчиках
        sensors_data = []
        for sensor in eq.sensors:
            last_reading = (
                db.query(SensorData)
                .filter(SensorData.sensor_id == sensor.id)
                .order_by(SensorData.timestamp.desc())
                .first()
            )
            
            sensors_data.append({
                "id": sensor.id,
                "sensor_id": sensor.sensor_id,
                "type": sensor.type,
                "location": sensor.location,
                "calibration_date": sensor.calibration_date,
                "equipment_id": sensor.equipment_id,
                "latest_value": last_reading.value if last_reading else None,
                "latest_unit": last_reading.unit if last_reading else None,
                "latest_timestamp": last_reading.timestamp if last_reading else None,
            })
        
        result.append(EquipmentWithMetrics(
            id=eq.id,
            equipment_id=eq.equipment_id,
            name=eq.name,
            type=eq.type,
            status=eq.status,
            location=eq.location,
            description=eq.description,
            installation_date=eq.installation_date,
            created_at=eq.created_at,
            updated_at=eq.updated_at,
            sensors=sensors_data,
            current_metrics=metrics,
            last_update=latest_data,
        ))
    
    return result


@router.get("/{equipment_id}", response_model=EquipmentWithMetrics)
async def get_equipment_detail(
    equipment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение детальной информации об оборудовании."""
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    metrics = eq.get_current_metrics(db)
    
    # Время последнего обновления
    latest_data = None
    for sensor in eq.sensors:
        last_reading = (
            db.query(SensorData)
            .filter(SensorData.sensor_id == sensor.id)
            .order_by(SensorData.timestamp.desc())
            .first()
        )
        if last_reading and (latest_data is None or last_reading.timestamp > latest_data):
            latest_data = last_reading.timestamp
    
    sensors_data = []
    for sensor in eq.sensors:
        last_reading = (
            db.query(SensorData)
            .filter(SensorData.sensor_id == sensor.id)
            .order_by(SensorData.timestamp.desc())
            .first()
        )
        
        sensors_data.append({
            "id": sensor.id,
            "sensor_id": sensor.sensor_id,
            "type": sensor.type,
            "location": sensor.location,
            "calibration_date": sensor.calibration_date,
            "equipment_id": sensor.equipment_id,
            "latest_value": last_reading.value if last_reading else None,
            "latest_unit": last_reading.unit if last_reading else None,
            "latest_timestamp": last_reading.timestamp if last_reading else None,
        })
    
    return EquipmentWithMetrics(
        id=eq.id,
        equipment_id=eq.equipment_id,
        name=eq.name,
        type=eq.type,
        status=eq.status,
        location=eq.location,
        description=eq.description,
        installation_date=eq.installation_date,
        created_at=eq.created_at,
        updated_at=eq.updated_at,
        sensors=sensors_data,
        current_metrics=metrics,
        last_update=latest_data,
    )


@router.post("", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment_data: EquipmentCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового оборудования.
    Часть метода configureSystem() из класса Administrator.
    Доступно только администраторам.
    Автоматически создаёт датчики для оборудования.
    """
    from models.equipment import Sensor, SensorType
    from datetime import date
    
    new_equipment = Equipment(
        equipment_id=f"EQ-{str(uuid.uuid4())[:8]}",
        name=equipment_data.name,
        type=equipment_data.type,
        location=equipment_data.location,
        description=equipment_data.description,
        installation_date=equipment_data.installation_date or date.today(),
        status=EquipmentStatus.ONLINE,
    )
    
    db.add(new_equipment)
    db.flush()  # Получаем ID для связи с датчиками
    
    # Автоматически создаём датчики для нового оборудования
    sensor_types = [
        (SensorType.TEMPERATURE, "°C"),
        (SensorType.VIBRATION, "мм/с"),
        (SensorType.PRESSURE, "кПа"),
        (SensorType.CURRENT, "А"),
    ]
    
    for sensor_type, unit in sensor_types:
        sensor = Sensor(
            sensor_id=f"SNS-{str(uuid.uuid4())[:8]}",
            type=sensor_type,
            location=f"{equipment_data.location or 'Не указано'}, {equipment_data.name}",
            calibration_date=date.today(),
            equipment_id=new_equipment.id,
        )
        db.add(sensor)
    
    db.commit()
    db.refresh(new_equipment)
    
    return new_equipment


@router.put("/{equipment_id}/status")
async def update_equipment_status(
    equipment_id: int,
    new_status: str,
    current_user: User = Depends(get_operator_user),
    db: Session = Depends(get_db)
):
    """
    Обновление статуса оборудования.
    Доступно операторам и выше (operator/administrator/manager).
    """
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    try:
        eq.status = EquipmentStatus(new_status)
        db.commit()
        return {"message": "Статус обновлён", "new_status": eq.status.value}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный статус: {new_status}"
        )


@router.get("/{equipment_id}/history", response_model=List[MaintenanceRecordResponse])
async def get_maintenance_history(
    equipment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение истории обслуживания оборудования.
    Реализация метода getMaintenanceHistory() из класса Equipment.
    """
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    records = (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.equipment_id == equipment_id)
        .order_by(MaintenanceRecord.date.desc())
        .all()
    )
    
    return [
        MaintenanceRecordResponse(
            id=r.id,
            record_id=r.record_id,
            date=r.date,
            description=r.description,
            technician=r.technician,
            equipment_id=r.equipment_id,
            notes=r.notes,
            is_completed=bool(r.is_completed),
            completed_at=r.completed_at,
            created_at=r.created_at,
        )
        for r in records
    ]


@router.post("/{equipment_id}/maintenance", status_code=status.HTTP_201_CREATED)
async def add_maintenance_record(
    equipment_id: int,
    record_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Добавление записи об обслуживании.
    Реализация метода performMaintenance() из класса Operator.
    """
    from datetime import date
    
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    new_record = MaintenanceRecord(
        record_id=f"MNT-{str(uuid.uuid4())[:8]}",
        date=date.fromisoformat(record_data.get("date", date.today().isoformat())),
        description=record_data.get("description", ""),
        technician=record_data.get("technician", current_user.username),
        equipment_id=equipment_id,
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    return {
        "message": "Запись создана",
        "record_id": new_record.record_id,
    }

