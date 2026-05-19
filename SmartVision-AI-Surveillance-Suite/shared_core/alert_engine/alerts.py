"""Alert models and dispatcher."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Protocol
from uuid import uuid4


class AlertPriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(slots=True)
class Alert:
    module: str
    camera_id: str
    title: str
    message: str
    priority: AlertPriority = AlertPriority.MEDIUM
    event_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    alert_id: str = field(default_factory=lambda: uuid4().hex)
    created_ts: float = field(default_factory=time.time)


class NotificationProvider(Protocol):
    def send(self, alert: Alert) -> None:
        ...


class AlertDispatcher:
    """Fan-out alerts to notification providers and in-memory subscribers."""

    def __init__(self, providers: list[NotificationProvider] | None = None) -> None:
        self.providers = providers or []
        self.recent_alerts: list[Alert] = []

    def dispatch(self, alert: Alert) -> Alert:
        self.recent_alerts.append(alert)
        self.recent_alerts = self.recent_alerts[-500:]
        for provider in self.providers:
            provider.send(alert)
        return alert
