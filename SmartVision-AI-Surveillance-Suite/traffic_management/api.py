"""FastAPI routes for the Traffic Management module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends

from shared_core.dashboard.auth import require_api_key
from shared_core.database.repository import EventRepository
from shared_core.utils.config import load_config


MODULE_NAME = "traffic_management"
CONFIG_PATH = Path(__file__).with_name("config.yaml")
router = APIRouter(prefix="/api/modules/traffic_management", tags=["Traffic Management"])


@router.get("/health")
def health() -> dict[str, Any]:
    return {"module": MODULE_NAME, "status": "ready", "config": str(CONFIG_PATH)}


@router.get("/features")
def features() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"module": MODULE_NAME, "features": data.get("module", {}).get("features", [])}


@router.get("/config", dependencies=[Depends(require_api_key)])
def config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


@router.get("/events", dependencies=[Depends(require_api_key)])
def events(limit: int = 50) -> list[dict[str, Any]]:
    return EventRepository.from_config(load_config(CONFIG_PATH)).list_events(module=MODULE_NAME, limit=limit)
