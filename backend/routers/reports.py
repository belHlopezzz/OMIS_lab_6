"""
Роутер отчётов.
Реализует методы generateReports() из Administrator и downloadReports() из Manager.
"""
from datetime import datetime, timedelta
from typing import Optional
import io

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, UserRole
from models.equipment import Equipment, Sensor, SensorData, Alert, AlertSeverity
from models.maintenance import MaintenanceRecord
from utils.dependencies import get_current_user, get_admin_user
from utils.reports import ReportGenerator


router = APIRouter()


@router.get("/pdf")
async def generate_pdf_report(
    period_days: int = Query(7, description="Период отчёта в днях"),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Генерация PDF отчёта.
    Реализация методов generateReports() и downloadReports().
    Доступно администраторам и менеджерам.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Собираем данные для отчёта
    report_data = _collect_report_data(db, start_date, end_date)
    
    # Генерируем PDF
    generator = ReportGenerator()
    pdf_buffer = generator.generate_pdf_report(report_data, start_date, end_date)
    
    filename = f"report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_buffer),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/csv")
async def generate_csv_report(
    period_days: int = Query(7, description="Период отчёта в днях"),
    data_type: str = Query("equipment", description="Тип данных: equipment, alerts, maintenance"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Генерация CSV отчёта.
    Доступно всем авторизованным пользователям.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    generator = ReportGenerator()
    
    if data_type == "equipment":
        equipment = db.query(Equipment).all()
        csv_content = generator.generate_equipment_csv(equipment, db)
    elif data_type == "alerts":
        alerts = db.query(Alert).filter(
            Alert.timestamp >= start_date,
            Alert.timestamp <= end_date
        ).all()
        csv_content = generator.generate_alerts_csv(alerts, db)
    elif data_type == "maintenance":
        records = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.date >= start_date.date(),
            MaintenanceRecord.date <= end_date.date()
        ).all()
        csv_content = generator.generate_maintenance_csv(records, db)
    else:
        csv_content = "Неверный тип данных"
    
    filename = f"{data_type}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    
    return Response(
        content=csv_content.encode('utf-8-sig'),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/summary")
async def get_report_summary(
    period_days: int = Query(7, description="Период в днях"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Сводка для отчёта без генерации файла.
    Используется для предпросмотра.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    return _collect_report_data(db, start_date, end_date)


def _collect_report_data(db: Session, start_date: datetime, end_date: datetime) -> dict:
    """Сбор данных для отчёта."""
    # Оборудование
    equipment = db.query(Equipment).all()
    
    # Оповещения за период
    alerts = db.query(Alert).filter(
        Alert.timestamp >= start_date,
        Alert.timestamp <= end_date
    ).all()
    
    critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
    warning_alerts = [a for a in alerts if a.severity == AlertSeverity.WARNING]
    
    # Обслуживание за период
    maintenance = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.date >= start_date.date(),
        MaintenanceRecord.date <= end_date.date()
    ).all()
    
    completed_maintenance = [m for m in maintenance if m.is_completed]
    
    # Статистика по оборудованию
    from models.equipment import EquipmentStatus
    online_count = sum(1 for e in equipment if e.status == EquipmentStatus.ONLINE)
    error_count = sum(1 for e in equipment if e.status == EquipmentStatus.ERROR)
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": (end_date - start_date).days,
        },
        "equipment": {
            "total": len(equipment),
            "online": online_count,
            "with_errors": error_count,
        },
        "alerts": {
            "total": len(alerts),
            "critical": len(critical_alerts),
            "warning": len(warning_alerts),
        },
        "maintenance": {
            "total": len(maintenance),
            "completed": len(completed_maintenance),
            "pending": len(maintenance) - len(completed_maintenance),
        },
        "recommendations": _generate_recommendations(equipment, alerts, db),
    }


def _generate_recommendations(equipment, alerts, db) -> list:
    """Генерация рекомендаций на основе данных."""
    recommendations = []
    
    from models.equipment import EquipmentStatus
    
    # Рекомендации по проблемному оборудованию
    for eq in equipment:
        if eq.status == EquipmentStatus.ERROR:
            recommendations.append(f"Требуется проверка оборудования: {eq.name}")
    
    # Рекомендации по частым оповещениям
    if len(alerts) > 10:
        recommendations.append("Высокое количество оповещений - рекомендуется комплексная диагностика")
    
    # Общие рекомендации
    if not recommendations:
        recommendations.append("Система работает в штатном режиме")
    
    return recommendations

