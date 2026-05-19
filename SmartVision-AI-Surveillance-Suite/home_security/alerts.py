"""Alert rules for home_security."""

from __future__ import annotations

from shared_core.alert_engine.alerts import Alert, AlertPriority


def build_event_alert(camera_id: str, title: str, message: str, event_id: str | None = None, priority: AlertPriority = AlertPriority.MEDIUM) -> Alert:
    return Alert(module="home_security", camera_id=camera_id, title=title, message=message, event_id=event_id, priority=priority)


class HomeSecurityAlertRules:
    def classify_priority(self, tags: list[str], score: float) -> AlertPriority:
        if score >= 0.80:
            return AlertPriority.CRITICAL
        if score >= 0.60:
            return AlertPriority.HIGH
        if tags:
            return AlertPriority.MEDIUM
        return AlertPriority.LOW
