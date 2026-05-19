"""Email, Telegram, SMS, and sound notification adapters.

Providers are intentionally no-op unless their environment variables are set,
which keeps local development and tests quiet.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

import requests

from shared_core.alert_engine.alerts import Alert


class EmailProvider:
    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.to = os.getenv("ALERT_EMAIL_TO")
        self.from_addr = os.getenv("ALERT_EMAIL_FROM", self.username or "smartvision@localhost")

    def send(self, alert: Alert) -> None:
        if not (self.host and self.to):
            return
        message = EmailMessage()
        message["Subject"] = f"[SmartVision] {alert.title}"
        message["From"] = self.from_addr
        message["To"] = self.to
        message.set_content(alert.message)
        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


class TelegramProvider:
    def __init__(self) -> None:
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def send(self, alert: Alert) -> None:
        if not (self.bot_token and self.chat_id):
            return
        requests.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={"chat_id": self.chat_id, "text": f"{alert.title}\n{alert.message}"},
            timeout=8,
        )


class SmsProvider:
    def send(self, alert: Alert) -> None:
        # Add a Twilio or local gateway implementation here when credentials are available.
        return


class SoundAlarmProvider:
    def send(self, alert: Alert) -> None:
        if os.getenv("ENABLE_SOUND_ALARMS", "false").lower() not in {"1", "true", "yes"}:
            return
        print("\a", end="")
