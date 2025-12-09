"""
Роутер событий и оповещений.
Реализует функционал NotificationSubsystem для работы с алертами.
"""
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.equipment import Alert, AlertSeverity, Equipment
from schemas.events import AlertResponse, EventResponse
from utils.dependencies import get_current_user


router = APIRouter()


@router.get("", response_model=List[EventResponse])
async def get_events(
    level: Optional[str] = Query(None, description="Уровень критичности"),
    hours: int = Query(72, description="Период в часах"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка событий и оповещений.
    Формат адаптирован под существующий фронтенд.
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    query = db.query(Alert).filter(Alert.timestamp >= start_time)
    
    if level and level != "all":
        try:
            severity = AlertSeverity(level)
            query = query.filter(Alert.severity == severity)
        except ValueError:
            pass
    
    alerts = query.order_by(Alert.timestamp.desc()).limit(100).all()
    
    result = []
    for alert in alerts:
        # Получаем название оборудования
        eq = db.query(Equipment).filter(Equipment.id == alert.equipment_id).first()
        device_name = eq.name if eq else f"Устройство #{alert.equipment_id}"
        
        result.append(EventResponse(
            id=alert.id,
            type="critical" if alert.severity == AlertSeverity.CRITICAL else "warning",
            device=device_name,
            message=alert.message,
            timestamp=alert.timestamp.strftime("%Y-%m-%d %H:%M"),
        ))
    
    return result


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    unread_only: bool = Query(False, description="Только непрочитанные"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение списка оповещений с полной информацией."""
    query = db.query(Alert)
    
    if unread_only:
        query = query.filter(Alert.is_read == 0)
    
    alerts = query.order_by(Alert.timestamp.desc()).limit(100).all()
    
    result = []
    for alert in alerts:
        eq = db.query(Equipment).filter(Equipment.id == alert.equipment_id).first()
        
        result.append(AlertResponse(
            id=alert.id,
            alert_id=alert.alert_id,
            severity=alert.severity,
            message=alert.message,
            timestamp=alert.timestamp,
            equipment_id=alert.equipment_id,
            equipment_name=eq.name if eq else None,
            sensor_id=alert.sensor_id,
            is_read=bool(alert.is_read),
            is_email_sent=bool(alert.is_email_sent),
        ))
    
    return result


@router.put("/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметить оповещение как прочитанное."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оповещение не найдено"
        )
    
    alert.is_read = 1
    db.commit()
    
    return {"message": "Оповещение отмечено как прочитанное"}


@router.put("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметить все оповещения как прочитанные."""
    db.query(Alert).filter(Alert.is_read == 0).update({"is_read": 1})
    db.commit()
    
    return {"message": "Все оповещения отмечены как прочитанные"}


@router.get("/stats")
async def get_alert_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Статистика по оповещениям."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    return {
        "unread_count": db.query(Alert).filter(Alert.is_read == 0).count(),
        "today_count": db.query(Alert).filter(Alert.timestamp >= today_start).count(),
        "week_count": db.query(Alert).filter(Alert.timestamp >= week_start).count(),
        "critical_unread": db.query(Alert).filter(
            Alert.is_read == 0,
            Alert.severity == AlertSeverity.CRITICAL
        ).count(),
    }

