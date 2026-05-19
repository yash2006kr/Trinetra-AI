"""FastAPI entrypoint for the SmartVision dashboard and module APIs."""

from __future__ import annotations

from importlib import import_module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared_core.dashboard.api import create_dashboard_router
from shared_core.stream_manager.camera import CameraConfig
from shared_core.stream_manager.camera_manager import CameraManager
from shared_core.utils.config import load_config


MODULES = [
    "highway_surveillance",
    "traffic_management",
    "smart_city_security",
    "retail_analytics",
    "industrial_safety",
    "smart_parking",
    "railway_surveillance",
    "campus_security",
    "home_security",
    "wildlife_monitoring",
]


def create_app() -> FastAPI:
    config = load_config()
    app = FastAPI(title="SmartVision AI Surveillance Suite", version="0.1.0")
    origins = config.get("dashboard", {}).get("cors_origins", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    camera_manager = CameraManager()
    for camera in config.get("cameras", []):
        camera_manager.add_camera(
            CameraConfig(**camera),
            start=bool(camera.get("enabled", False)),
        )

    app.include_router(create_dashboard_router(camera_manager=camera_manager))

    for module_name in MODULES:
        try:
            module = import_module(f"{module_name}.api")
            app.include_router(module.router)
        except Exception:
            # Modules are optional/import-safe; missing heavyweight dependencies in
            # one domain should not prevent the dashboard from starting.
            continue

    @app.on_event("shutdown")
    def shutdown() -> None:
        camera_manager.stop_all()

    return app


app = create_app()
