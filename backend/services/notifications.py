"""
Подсистема уведомлений (NotificationSubsystem).
Реализация интерфейса Notifier из UML диаграммы.

Примечание к диаграмме: атрибут smsService удалён согласно требованиям -
используется только email для всех уведомлений.
"""
import smtplib
import logging
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM
from models.equipment import Alert, AlertSeverity, Equipment
from models.user import User


logger = logging.getLogger(__name__)


class Notifier(ABC):
    """
    Интерфейс Notifier из UML диаграммы.
    Определяет методы для отправки уведомлений и генерации отчётов.
    """
    
    @abstractmethod
    def send_alert(self, alert: Alert, recipients: List[str]) -> bool:
        """Отправка оповещения."""
        pass
    
    @abstractmethod
    def generate_report(self, data: dict) -> str:
        """Генерация текстового отчёта."""
        pass


class NotificationSubsystem(Notifier):
    """
    Реализация подсистемы уведомлений.
    
    Атрибуты из диаграммы:
    - emailService: EmailService - сервис email (реализован через smtplib)
    - smsService: SMSService - УДАЛЁН (используем только email)
    
    Методы из диаграммы:
    - createNotification() - создание уведомления
    - formatReport() - форматирование отчёта
    - deliverAlert() - доставка оповещения
    """
    
    def __init__(self):
        self._smtp_host = SMTP_HOST
        self._smtp_port = SMTP_PORT
        self._smtp_user = SMTP_USER
        self._smtp_password = SMTP_PASSWORD
        self._email_from = EMAIL_FROM
    
    def send_alert(self, alert: Alert, recipients: List[str]) -> bool:
        """
        Отправка оповещения по email.
        Реализация метода deliverAlert() из диаграммы.
        """
        if not recipients:
            logger.warning("Нет получателей для оповещения")
            return False
        
        subject = self._format_alert_subject(alert)
        body = self._format_alert_body(alert)
        
        return self._send_email(recipients, subject, body)
    
    def generate_report(self, data: dict) -> str:
        """
        Генерация текстового отчёта.
        Реализация метода formatReport() из диаграммы.
        """
        report_lines = [
            "=" * 50,
            "ОТЧЁТ О СОСТОЯНИИ СИСТЕМЫ",
            f"Дата: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
            "",
        ]
        
        # Период отчёта
        period = data.get("period", {})
        report_lines.append(f"Период: {period.get('start', 'N/A')} - {period.get('end', 'N/A')}")
        report_lines.append("")
        
        # Статистика оборудования
        equipment = data.get("equipment", {})
        report_lines.append("ОБОРУДОВАНИЕ:")
        report_lines.append(f"  Всего: {equipment.get('total', 0)}")
        report_lines.append(f"  В работе: {equipment.get('online', 0)}")
        report_lines.append(f"  С ошибками: {equipment.get('with_errors', 0)}")
        report_lines.append("")
        
        # Статистика оповещений
        alerts = data.get("alerts", {})
        report_lines.append("ОПОВЕЩЕНИЯ:")
        report_lines.append(f"  Всего: {alerts.get('total', 0)}")
        report_lines.append(f"  Критических: {alerts.get('critical', 0)}")
        report_lines.append(f"  Предупреждений: {alerts.get('warning', 0)}")
        report_lines.append("")
        
        # Обслуживание
        maintenance = data.get("maintenance", {})
        report_lines.append("ОБСЛУЖИВАНИЕ:")
        report_lines.append(f"  Всего работ: {maintenance.get('total', 0)}")
        report_lines.append(f"  Завершено: {maintenance.get('completed', 0)}")
        report_lines.append(f"  В процессе: {maintenance.get('pending', 0)}")
        report_lines.append("")
        
        # Рекомендации
        recommendations = data.get("recommendations", [])
        if recommendations:
            report_lines.append("РЕКОМЕНДАЦИИ:")
            for rec in recommendations:
                report_lines.append(f"  • {rec}")
        
        report_lines.append("")
        report_lines.append("=" * 50)
        
        return "\n".join(report_lines)
    
    def create_notification(
        self, 
        db: Session,
        equipment: Equipment,
        message: str,
        severity: AlertSeverity
    ) -> Alert:
        """
        Создание нового уведомления.
        Реализация метода createNotification() из диаграммы.
        """
        import uuid
        
        alert = Alert(
            alert_id=f"ALR-{str(uuid.uuid4())[:8]}",
            severity=severity,
            message=message,
            equipment_id=equipment.id,
        )
        
        db.add(alert)
        db.flush()
        
        return alert
    
    def send_daily_report(self, db: Session, report_data: dict):
        """Отправка ежедневного отчёта администраторам."""
        from models.user import UserRole
        
        # Получаем всех администраторов и менеджеров
        admins = db.query(User).filter(
            User.user_type.in_([UserRole.ADMINISTRATOR, UserRole.MANAGER])
        ).all()
        
        recipients = [u.email for u in admins if u.email]
        
        if not recipients:
            logger.warning("Нет получателей для ежедневного отчёта")
            return
        
        subject = f"Ежедневный отчёт IoT Monitor - {datetime.utcnow().strftime('%Y-%m-%d')}"
        body = self.generate_report(report_data)
        
        self._send_email(recipients, subject, body)
    
    def notify_critical_alert(self, db: Session, alert: Alert):
        """Немедленное уведомление о критическом событии."""
        # Получаем всех пользователей
        users = db.query(User).all()
        recipients = [u.email for u in users if u.email]
        
        if not recipients:
            return
        
        self.send_alert(alert, recipients)
        
        # Отмечаем что email отправлен
        alert.is_email_sent = 1
        db.commit()
    
    def _format_alert_subject(self, alert: Alert) -> str:
        """Форматирование темы письма для оповещения."""
        severity_text = "КРИТИЧНО" if alert.severity == AlertSeverity.CRITICAL else "Предупреждение"
        return f"[IoT Monitor] {severity_text}: Оповещение #{alert.alert_id}"
    
    def _format_alert_body(self, alert: Alert) -> str:
        """Форматирование тела письма для оповещения."""
        lines = [
            f"Уровень: {'КРИТИЧЕСКИЙ' if alert.severity == AlertSeverity.CRITICAL else 'Предупреждение'}",
            f"Время: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Оборудование ID: {alert.equipment_id}",
            "",
            "Сообщение:",
            alert.message,
            "",
            "---",
            "Это автоматическое уведомление системы IoT Monitor.",
            "Не отвечайте на это письмо.",
        ]
        
        return "\n".join(lines)
    
    def _send_email(self, recipients: List[str], subject: str, body: str) -> bool:
        """
        Отправка email через SMTP.
        Внутренняя реализация emailService из диаграммы.
        """
        if not self._smtp_user or not self._smtp_password:
            logger.warning("SMTP не настроен, email не отправлен")
            logger.warning(f"SMTP_USER: {'установлен' if self._smtp_user else 'НЕ УСТАНОВЛЕН'}")
            logger.warning(f"SMTP_PASSWORD: {'установлен' if self._smtp_password else 'НЕ УСТАНОВЛЕН'}")
            logger.info(f"Email (симуляция) -> {recipients}: {subject}")
            logger.info(f"Текст письма:\n{body}")
            return False  # Возвращаем False чтобы показать что email не отправлен
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self._email_from
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            logger.info(f"Попытка отправки email через {self._smtp_host}:{self._smtp_port}")
            logger.info(f"От: {self._smtp_user}, Кому: {recipients}")
            
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.sendmail(self._email_from, recipients, msg.as_string())
            
            logger.info(f"✓ Email успешно отправлен: {recipients}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Ошибка аутентификации SMTP: {e}")
            logger.error("Проверьте правильность SMTP_USER и SMTP_PASSWORD (используйте App Password для Gmail)")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Ошибка SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка отправки email: {e}", exc_info=True)
            return False

