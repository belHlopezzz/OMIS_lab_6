"""
Генератор отчётов.
Создание PDF и CSV отчётов для экспорта данных.
"""
import io
import csv
from datetime import datetime
from typing import List, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from sqlalchemy.orm import Session

from models.equipment import Equipment, Alert, SensorData
from models.maintenance import MaintenanceRecord


class ReportGenerator:
    """
    Генератор отчётов в форматах PDF и CSV.
    Реализует функционал для методов generateReports() и downloadReports().
    """
    
    def __init__(self):
        self._styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _setup_styles(self):
        """Настройка стилей для PDF."""
        # Добавляем кастомные стили
        self._styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self._styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # центр
        ))
        
        self._styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self._styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
        ))
    
    def generate_pdf_report(
        self, 
        report_data: Dict, 
        start_date: datetime,
        end_date: datetime
    ) -> bytes:
        """
        Генерация PDF отчёта.
        
        Args:
            report_data: данные для отчёта
            start_date: начало периода
            end_date: конец периода
            
        Returns:
            PDF документ в виде байтов
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        elements = []
        
        # Заголовок
        elements.append(Paragraph(
            "Otchet o sostoyanii sistemy IoT Monitor",
            self._styles['ReportTitle']
        ))
        
        # Период
        period_text = f"Period: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        elements.append(Paragraph(period_text, self._styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Статистика оборудования
        elements.append(Paragraph("Oborudovanie", self._styles['SectionTitle']))
        equipment_data = report_data.get("equipment", {})
        equipment_table = [
            ["Parametr", "Znachenie"],
            ["Vsego ustroystv", str(equipment_data.get("total", 0))],
            ["V rabote", str(equipment_data.get("online", 0))],
            ["S oshibkami", str(equipment_data.get("with_errors", 0))],
        ]
        elements.append(self._create_table(equipment_table))
        elements.append(Spacer(1, 15))
        
        # Статистика оповещений
        elements.append(Paragraph("Opovescheniya", self._styles['SectionTitle']))
        alerts_data = report_data.get("alerts", {})
        alerts_table = [
            ["Parametr", "Znachenie"],
            ["Vsego", str(alerts_data.get("total", 0))],
            ["Kriticheskih", str(alerts_data.get("critical", 0))],
            ["Preduprezhdeniy", str(alerts_data.get("warning", 0))],
        ]
        elements.append(self._create_table(alerts_table))
        elements.append(Spacer(1, 15))
        
        # Обслуживание
        elements.append(Paragraph("Obsluzhivanie", self._styles['SectionTitle']))
        maintenance_data = report_data.get("maintenance", {})
        maintenance_table = [
            ["Parametr", "Znachenie"],
            ["Vsego rabot", str(maintenance_data.get("total", 0))],
            ["Zaversheno", str(maintenance_data.get("completed", 0))],
            ["V processe", str(maintenance_data.get("pending", 0))],
        ]
        elements.append(self._create_table(maintenance_table))
        elements.append(Spacer(1, 15))
        
        # Рекомендации
        recommendations = report_data.get("recommendations", [])
        if recommendations:
            elements.append(Paragraph("Rekomendacii", self._styles['SectionTitle']))
            for rec in recommendations:
                # Транслитерация для PDF без кириллицы
                rec_translit = self._transliterate(rec)
                elements.append(Paragraph(f"- {rec_translit}", self._styles['Normal']))
        
        # Футер
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"Otchet sformirovan: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            self._styles['Normal']
        ))
        
        doc.build(elements)
        
        return buffer.getvalue()
    
    def _create_table(self, data: List[List[str]]) -> Table:
        """Создание стилизованной таблицы."""
        table = Table(data, colWidths=[10*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        return table
    
    def _transliterate(self, text: str) -> str:
        """Простая транслитерация кириллицы в латиницу."""
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
            'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        }
        result = []
        for char in text:
            result.append(translit_map.get(char, char))
        return ''.join(result)
    
    def generate_equipment_csv(self, equipment_list: List[Equipment], db: Session) -> str:
        """
        Генерация CSV отчёта по оборудованию.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            "ID", "Название", "Тип", "Статус", "Расположение",
            "Дата установки", "Последнее обновление"
        ])
        
        for eq in equipment_list:
            # Получаем время последнего обновления данных
            last_update = None
            for sensor in eq.sensors:
                last_data = (
                    db.query(SensorData)
                    .filter(SensorData.sensor_id == sensor.id)
                    .order_by(SensorData.timestamp.desc())
                    .first()
                )
                if last_data and (last_update is None or last_data.timestamp > last_update):
                    last_update = last_data.timestamp
            
            writer.writerow([
                eq.equipment_id,
                eq.name,
                eq.type,
                eq.status.value,
                eq.location or "",
                eq.installation_date.strftime("%Y-%m-%d") if eq.installation_date else "",
                last_update.strftime("%Y-%m-%d %H:%M") if last_update else "",
            ])
        
        return output.getvalue()
    
    def generate_alerts_csv(self, alerts: List[Alert], db: Session) -> str:
        """
        Генерация CSV отчёта по оповещениям.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            "ID", "Время", "Уровень", "Оборудование", "Сообщение", "Прочитано"
        ])
        
        for alert in alerts:
            eq = db.query(Equipment).filter(Equipment.id == alert.equipment_id).first()
            
            writer.writerow([
                alert.alert_id,
                alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                alert.severity.value,
                eq.name if eq else f"ID: {alert.equipment_id}",
                alert.message,
                "Да" if alert.is_read else "Нет",
            ])
        
        return output.getvalue()
    
    def generate_maintenance_csv(self, records: List[MaintenanceRecord], db: Session) -> str:
        """
        Генерация CSV отчёта по обслуживанию.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            "ID", "Дата", "Оборудование", "Описание", "Техник", "Статус", "Заметки"
        ])
        
        for record in records:
            eq = db.query(Equipment).filter(Equipment.id == record.equipment_id).first()
            
            writer.writerow([
                record.record_id,
                record.date.strftime("%Y-%m-%d"),
                eq.name if eq else f"ID: {record.equipment_id}",
                record.description,
                record.technician,
                "Завершено" if record.is_completed else "В процессе",
                record.notes or "",
            ])
        
        return output.getvalue()
    
    def generate_sensor_data_csv(
        self, 
        sensor_data: List[SensorData],
        db: Session
    ) -> str:
        """
        Генерация CSV отчёта по данным датчиков.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            "Время", "Датчик ID", "Тип датчика", "Значение", "Единица измерения"
        ])
        
        for data in sensor_data:
            writer.writerow([
                data.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                data.sensor.sensor_id if data.sensor else "",
                data.sensor.type.value if data.sensor else "",
                data.value,
                data.unit,
            ])
        
        return output.getvalue()

