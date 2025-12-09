"""
Генератор отчётов.
Создание PDF и CSV отчётов для экспорта данных.
"""

import csv
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from models.equipment import Alert, Equipment, SensorData
from models.maintenance import MaintenanceRecord
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Генератор отчётов в форматах PDF и CSV.
    Реализует функционал для методов generateReports() и downloadReports().
    """

    def __init__(self):
        self._styles = getSampleStyleSheet()
        self._setup_fonts()
        self._setup_styles()

    def _setup_fonts(self):
        """Настройка шрифтов с поддержкой кириллицы."""
        try:
            # Пробуем использовать системные шрифты с поддержкой кириллицы
            # На macOS обычно есть Arial Unicode MS или Helvetica
            system_fonts = [
                "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]

            font_registered = False
            for font_path in system_fonts:
                if Path(font_path).exists():
                    try:
                        # Регистрируем TTF шрифт
                        pdfmetrics.registerFont(TTFont("CyrillicFont", font_path))
                        font_registered = True
                        logger.info(
                            f"Зарегистрирован шрифт с поддержкой кириллицы: {font_path}"
                        )
                        break
                    except Exception as e:
                        logger.warning(f"Не удалось загрузить шрифт {font_path}: {e}")
                        continue

            if not font_registered:
                # Если системные шрифты не найдены, используем Helvetica
                # ReportLab может отображать кириллицу через Helvetica при правильной обработке
                logger.info("Системные шрифты не найдены, используется Helvetica")
                self._font_name = "Helvetica"
            else:
                self._font_name = "CyrillicFont"

        except Exception as e:
            logger.warning(f"Ошибка настройки шрифтов: {e}, используем Helvetica")
            self._font_name = "Helvetica"

    def _setup_styles(self):
        """Настройка стилей для PDF."""
        # Добавляем кастомные стили с поддержкой кириллицы
        self._styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self._styles["Heading1"],
                fontName=self._font_name,
                fontSize=18,
                spaceAfter=30,
                alignment=1,  # центр
            )
        )

        self._styles.add(
            ParagraphStyle(
                name="SectionTitle",
                parent=self._styles["Heading2"],
                fontName=self._font_name,
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
            )
        )

        # Обновляем базовые стили для использования правильного шрифта
        self._styles["Normal"].fontName = self._font_name
        self._styles["Heading1"].fontName = self._font_name
        self._styles["Heading2"].fontName = self._font_name

    def generate_pdf_report(
        self, report_data: Dict, start_date: datetime, end_date: datetime
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
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []

        # Заголовок
        elements.append(
            Paragraph(
                "Отчёт о состоянии системы IoT Monitor", self._styles["ReportTitle"]
            )
        )

        # Период
        period_text = f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"
        elements.append(Paragraph(period_text, self._styles["Normal"]))
        elements.append(Spacer(1, 20))

        # Статистика оборудования
        elements.append(Paragraph("Оборудование", self._styles["SectionTitle"]))
        equipment_data = report_data.get("equipment", {})
        equipment_table = [
            ["Параметр", "Значение"],
            ["Всего устройств", str(equipment_data.get("total", 0))],
            ["В работе", str(equipment_data.get("online", 0))],
            ["С ошибками", str(equipment_data.get("with_errors", 0))],
        ]
        elements.append(self._create_table(equipment_table))
        elements.append(Spacer(1, 15))

        # Статистика оповещений
        elements.append(Paragraph("Оповещения", self._styles["SectionTitle"]))
        alerts_data = report_data.get("alerts", {})
        alerts_table = [
            ["Параметр", "Значение"],
            ["Всего", str(alerts_data.get("total", 0))],
            ["Критических", str(alerts_data.get("critical", 0))],
            ["Предупреждений", str(alerts_data.get("warning", 0))],
        ]
        elements.append(self._create_table(alerts_table))
        elements.append(Spacer(1, 15))

        # Обслуживание
        elements.append(Paragraph("Обслуживание", self._styles["SectionTitle"]))
        maintenance_data = report_data.get("maintenance", {})
        maintenance_table = [
            ["Параметр", "Значение"],
            ["Всего работ", str(maintenance_data.get("total", 0))],
            ["Завершено", str(maintenance_data.get("completed", 0))],
            ["В процессе", str(maintenance_data.get("pending", 0))],
        ]
        elements.append(self._create_table(maintenance_table))
        elements.append(Spacer(1, 15))

        # Рекомендации
        recommendations = report_data.get("recommendations", [])
        if recommendations:
            elements.append(Paragraph("Рекомендации", self._styles["SectionTitle"]))
            for rec in recommendations:
                elements.append(Paragraph(f"• {rec}", self._styles["Normal"]))

        # Футер
        elements.append(Spacer(1, 30))
        elements.append(
            Paragraph(
                f"Отчёт сформирован: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
                self._styles["Normal"],
            )
        )

        doc.build(elements)

        return buffer.getvalue()

    def _create_table(self, data: List[List[str]]) -> Table:
        """Создание стилизованной таблицы с поддержкой кириллицы."""
        # Преобразуем данные в Paragraph для правильного отображения кириллицы
        table_data = []
        for row in data:
            table_row = []
            for cell in row:
                # Используем Paragraph для поддержки кириллицы
                table_row.append(Paragraph(str(cell), self._styles["Normal"]))
            table_data.append(table_row)

        table = Table(table_data, colWidths=[10 * cm, 5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    def generate_equipment_csv(
        self, equipment_list: List[Equipment], db: Session
    ) -> str:
        """
        Генерация CSV отчёта по оборудованию.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Заголовки
        writer.writerow(
            [
                "ID",
                "Название",
                "Тип",
                "Статус",
                "Расположение",
                "Дата установки",
                "Последнее обновление",
            ]
        )

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
                if last_data and (
                    last_update is None or last_data.timestamp > last_update
                ):
                    last_update = last_data.timestamp

            writer.writerow(
                [
                    eq.equipment_id,
                    eq.name,
                    eq.type,
                    eq.status.value,
                    eq.location or "",
                    eq.installation_date.strftime("%Y-%m-%d")
                    if eq.installation_date
                    else "",
                    last_update.strftime("%Y-%m-%d %H:%M") if last_update else "",
                ]
            )

        return output.getvalue()

    def generate_alerts_csv(self, alerts: List[Alert], db: Session) -> str:
        """
        Генерация CSV отчёта по оповещениям.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Заголовки
        writer.writerow(
            ["ID", "Время", "Уровень", "Оборудование", "Сообщение", "Прочитано"]
        )

        for alert in alerts:
            eq = db.query(Equipment).filter(Equipment.id == alert.equipment_id).first()

            writer.writerow(
                [
                    alert.alert_id,
                    alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    alert.severity.value,
                    eq.name if eq else f"ID: {alert.equipment_id}",
                    alert.message,
                    "Да" if alert.is_read else "Нет",
                ]
            )

        return output.getvalue()

    def generate_maintenance_csv(
        self, records: List[MaintenanceRecord], db: Session
    ) -> str:
        """
        Генерация CSV отчёта по обслуживанию.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Заголовки
        writer.writerow(
            ["ID", "Дата", "Оборудование", "Описание", "Техник", "Статус", "Заметки"]
        )

        for record in records:
            eq = db.query(Equipment).filter(Equipment.id == record.equipment_id).first()

            writer.writerow(
                [
                    record.record_id,
                    record.date.strftime("%Y-%m-%d"),
                    eq.name if eq else f"ID: {record.equipment_id}",
                    record.description,
                    record.technician,
                    "Завершено" if record.is_completed else "В процессе",
                    record.notes or "",
                ]
            )

        return output.getvalue()

    def generate_sensor_data_csv(
        self, sensor_data: List[SensorData], db: Session
    ) -> str:
        """
        Генерация CSV отчёта по данным датчиков.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Заголовки
        writer.writerow(
            ["Время", "Датчик ID", "Тип датчика", "Значение", "Единица измерения"]
        )

        for data in sensor_data:
            writer.writerow(
                [
                    data.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    data.sensor.sensor_id if data.sensor else "",
                    data.sensor.type.value if data.sensor else "",
                    data.value,
                    data.unit,
                ]
            )

        return output.getvalue()
