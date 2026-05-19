"""SQLAlchemy metadata schema."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Camera(Base):
    __tablename__ = "cameras"

    camera_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    module: Mapped[str | None] = mapped_column(String(80), index=True)
    name: Mapped[str | None] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(1024))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    events: Mapped[list["Event"]] = relationship(back_populates="camera")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    module: Mapped[str] = mapped_column(String(80), index=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.camera_id"), index=True)
    clip_path: Mapped[str | None] = mapped_column(String(2048))
    snapshot_path: Mapped[str | None] = mapped_column(String(2048))
    start_ts: Mapped[float] = mapped_column(Float, index=True)
    end_ts: Mapped[float | None] = mapped_column(Float)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    tags: Mapped[list | None] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    camera: Mapped[Camera] = relationship(back_populates="events")
    alerts: Mapped[list["AlertRecord"]] = relationship(back_populates="event")


class AlertRecord(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.event_id"), nullable=True)
    module: Mapped[str] = mapped_column(String(80), index=True)
    camera_id: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_ts: Mapped[float] = mapped_column(Float, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped[Event | None] = relationship(back_populates="alerts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(160), index=True)
    target: Mapped[str | None] = mapped_column(String(200))
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModuleHealth(Base):
    __tablename__ = "module_health"

    module: Mapped[str] = mapped_column(String(80), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="unknown")
    last_heartbeat_ts: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
