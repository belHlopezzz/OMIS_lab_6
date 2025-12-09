"""
Роутер дашборда.
Предоставляет статистику и данные для графиков на главной странице.
"""
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.user import User
from models.equipment import Equipment, EquipmentStatus, Sensor, SensorData, SensorType, Alert
from schemas.dashboard import DashboardStats, ChartDataPoint, TemperatureChartData
from utils.dependencies import get_current_user


router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение общей статистики для дашборда.
    Включает количество устройств по статусам и оповещения.
    """
    # Считаем устройства по статусам
    total = db.query(Equipment).count()
    online = db.query(Equipment).filter(Equipment.status == EquipmentStatus.ONLINE).count()
    error = db.query(Equipment).filter(Equipment.status == EquipmentStatus.ERROR).count()
    offline = db.query(Equipment).filter(Equipment.status == EquipmentStatus.OFFLINE).count()
    maintenance = db.query(Equipment).filter(Equipment.status == EquipmentStatus.MAINTENANCE).count()
    
    # Считаем оповещения за сегодня
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    alerts_today = db.query(Alert).filter(Alert.timestamp >= today_start).count()
    critical_alerts = db.query(Alert).filter(
        Alert.timestamp >= today_start,
        Alert.severity == "critical"
    ).count()
    
    return DashboardStats(
        total_devices=total,
        online_devices=online,
        error_devices=error,
        offline_devices=offline,
        maintenance_devices=maintenance,
        total_alerts_today=alerts_today,
        critical_alerts=critical_alerts,
    )


@router.get("/temperature-chart", response_model=TemperatureChartData)
async def get_temperature_chart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение данных для графика средней температуры системы.
    Возвращает агрегированные данные за последние 24 часа.
    """
    now = datetime.utcnow()
    start_time = now - timedelta(hours=24)
    
    # Получаем все температурные датчики
    temp_sensors = db.query(Sensor).filter(Sensor.type == SensorType.TEMPERATURE).all()
    sensor_ids = [s.id for s in temp_sensors]
    
    if not sensor_ids:
        # Возвращаем пустые данные если датчиков нет
        return TemperatureChartData(
            data=[],
            avg_value=0,
            min_value=0,
            max_value=0,
        )
    
    # Группируем данные по 4-часовым интервалам
    chart_data = []
    all_values = []
    
    for hours_offset in range(0, 24, 4):
        interval_start = start_time + timedelta(hours=hours_offset)
        interval_end = interval_start + timedelta(hours=4)
        
        # Средняя температура за интервал
        avg_temp = db.query(func.avg(SensorData.value)).filter(
            SensorData.sensor_id.in_(sensor_ids),
            SensorData.timestamp >= interval_start,
            SensorData.timestamp < interval_end
        ).scalar()
        
        if avg_temp is not None:
            all_values.append(avg_temp)
            chart_data.append(ChartDataPoint(
                time=interval_start.strftime("%H:%M"),
                value=round(avg_temp, 1)
            ))
    
    # Добавляем текущее значение
    current_avg = db.query(func.avg(SensorData.value)).filter(
        SensorData.sensor_id.in_(sensor_ids),
        SensorData.timestamp >= now - timedelta(minutes=30)
    ).scalar()
    
    if current_avg:
        all_values.append(current_avg)
        chart_data.append(ChartDataPoint(
            time=now.strftime("%H:%M"),
            value=round(current_avg, 1)
        ))
    
    return TemperatureChartData(
        data=chart_data,
        avg_value=round(sum(all_values) / len(all_values), 1) if all_values else 0,
        min_value=round(min(all_values), 1) if all_values else 0,
        max_value=round(max(all_values), 1) if all_values else 0,
    )


@router.get("/sensor-stats")
async def get_sensor_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение текущей статистики по всем типам датчиков.
    Используется для отображения сводных показателей.
    """
    now = datetime.utcnow()
    recent_time = now - timedelta(minutes=10)
    
    stats = {}
    
    for sensor_type in SensorType:
        sensors = db.query(Sensor).filter(Sensor.type == sensor_type).all()
        sensor_ids = [s.id for s in sensors]
        
        if sensor_ids:
            # Последние значения
            latest_values = db.query(SensorData.value).filter(
                SensorData.sensor_id.in_(sensor_ids),
                SensorData.timestamp >= recent_time
            ).all()
            
            values = [v[0] for v in latest_values]
            
            if values:
                stats[sensor_type.value] = {
                    "avg": round(sum(values) / len(values), 2),
                    "min": round(min(values), 2),
                    "max": round(max(values), 2),
                    "count": len(sensors),
                }
    
    return stats

