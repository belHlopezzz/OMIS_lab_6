"""
Сервис отправки email.
Обёртка над smtplib для удобного использования.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional
from pathlib import Path

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM


logger = logging.getLogger(__name__)


class EmailService:
    """
    Сервис для отправки email.
    Поддерживает текстовые письма и вложения.
    """
    
    def __init__(
        self,
        smtp_host: str = SMTP_HOST,
        smtp_port: int = SMTP_PORT,
        username: str = SMTP_USER,
        password: str = SMTP_PASSWORD,
        from_address: str = EMAIL_FROM,
    ):
        self._host = smtp_host
        self._port = smtp_port
        self._username = username
        self._password = password
        self._from = from_address
    
    def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: Optional[str] = None,
        attachments: Optional[List[Path]] = None,
    ) -> bool:
        """
        Отправка email.
        
        Args:
            to: список получателей
            subject: тема письма
            body: текстовое содержимое
            html: HTML версия (опционально)
            attachments: список файлов для прикрепления
            
        Returns:
            True если отправка успешна
        """
        if not self._username or not self._password:
            logger.warning("SMTP не настроен")
            self._log_email(to, subject, body)
            return True
        
        try:
            msg = self._create_message(to, subject, body, html, attachments)
            self._send_message(msg, to)
            logger.info(f"Email отправлен: {to}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False
    
    def _create_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: Optional[str],
        attachments: Optional[List[Path]],
    ) -> MIMEMultipart:
        """Создание MIME сообщения."""
        msg = MIMEMultipart("alternative" if html else "mixed")
        msg["From"] = self._from
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        
        # Текстовая версия
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        # HTML версия если есть
        if html:
            msg.attach(MIMEText(html, "html", "utf-8"))
        
        # Вложения
        if attachments:
            for file_path in attachments:
                if file_path.exists():
                    with open(file_path, "rb") as f:
                        attachment = MIMEApplication(f.read())
                        attachment.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=file_path.name
                        )
                        msg.attach(attachment)
        
        return msg
    
    def _send_message(self, msg: MIMEMultipart, recipients: List[str]):
        """Отправка сообщения через SMTP."""
        with smtplib.SMTP(self._host, self._port) as server:
            server.starttls()
            server.login(self._username, self._password)
            server.sendmail(self._from, recipients, msg.as_string())
    
    def _log_email(self, to: List[str], subject: str, body: str):
        """Логирование email при отсутствии SMTP."""
        logger.info(f"[Email симуляция] To: {to}")
        logger.info(f"[Email симуляция] Subject: {subject}")
        logger.debug(f"[Email симуляция] Body: {body[:200]}...")

