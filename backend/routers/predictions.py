"""
Роутер прогнозирования.
Реализует методы analyzeData() из Administrator и функционал AnalysisSubsystem.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.equipment import Equipment, Sensor, SensorData
from schemas.prediction import PredictionRequest, PredictionResponse, FailurePrediction
from utils.dependencies import get_current_user, get_admin_user
from services.analysis import AnalysisSubsystem


router = APIRouter()

# Глобальный экземпляр подсистемы анализа
analysis_subsystem = AnalysisSubsystem()


@router.post("/{equipment_id}", response_model=PredictionResponse)
async def predict_failure(
    equipment_id: int,
    request: PredictionRequest = None,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Прогнозирование отказа оборудования.
    Реализация методов analyzeData() и generatePredictions() из AnalysisSubsystem.
    Доступно администраторам и менеджерам.
    """
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    horizon = request.horizon_hours if request else 48
    
    # Запускаем прогнозирование
    prediction_result = analysis_subsystem.predict_failure(db, equipment_id, horizon)
    
    return PredictionResponse(
        equipment_id=eq.id,
        equipment_name=eq.name,
        prediction_time=datetime.utcnow(),
        failure_prediction=prediction_result["prediction"],
        recommendations=prediction_result["recommendations"],
        current_status=eq.status.value,
    )


@router.get("/{equipment_id}/anomalies")
async def detect_anomalies(
    equipment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обнаружение аномалий в данных датчиков.
    Реализация метода detectAnomalies() из интерфейса Analyzer.
    """
    eq = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оборудование не найдено"
        )
    
    anomalies = analysis_subsystem.detect_anomalies(db, equipment_id)
    
    return {
        "equipment_id": equipment_id,
        "equipment_name": eq.name,
        "check_time": datetime.utcnow().isoformat(),
        "anomalies": anomalies,
        "has_anomalies": any(a["is_anomaly"] for a in anomalies),
    }


@router.get("/batch")
async def predict_all_equipment(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Массовое прогнозирование для всего оборудования.
    Возвращает сводку по рискам.
    """
    equipment_list = db.query(Equipment).all()
    
    results = []
    high_risk_count = 0
    
    for eq in equipment_list:
        try:
            prediction_result = analysis_subsystem.predict_failure(db, eq.id, 48)
            risk_level = prediction_result["prediction"].risk_level
            
            if risk_level in ("high", "critical"):
                high_risk_count += 1
            
            results.append({
                "equipment_id": eq.id,
                "equipment_name": eq.name,
                "risk_level": risk_level,
                "probability": prediction_result["prediction"].probability,
            })
        except Exception:
            results.append({
                "equipment_id": eq.id,
                "equipment_name": eq.name,
                "risk_level": "unknown",
                "probability": 0,
            })
    
    # Сортируем по риску
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    results.sort(key=lambda x: risk_order.get(x["risk_level"], 5))
    
    return {
        "total_equipment": len(equipment_list),
        "high_risk_count": high_risk_count,
        "predictions": results,
    }

