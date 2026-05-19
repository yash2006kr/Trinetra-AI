# SmartVision AI Surveillance Suite

Production-oriented, modular AI CCTV surveillance starter built with Python, OpenCV, YOLOv8/YOLOv11-compatible Ultralytics models, FastAPI, SQLite/PostgreSQL, and a React monitoring dashboard.

## What Is Included

- Ten independent surveillance domains: highway, traffic, city security, retail, industrial safety, parking, railway, campus, home, and wildlife.
- Shared reusable core for motion detection, event recording, camera threads, alerts, tracking, model loading, database storage, notifications, and dashboard APIs.
- Motion-triggered recording only: pre-event buffer, idle stop timeout, background subtraction, frame differencing, scene-change suppression, snapshots for minor events, retention pruning, and clip metadata sidecars.
- YOLO model adapter with GPU auto-detection and half precision when CUDA is available.
- Thread-safe multi-camera manager with webcam, file, RTSP, and IP stream support.
- FastAPI REST and WebSocket backend plus React dashboard.
- Docker and Docker Compose for API, PostgreSQL, and frontend.
- Unit tests, benchmark script, setup scripts, and sample-video generator.

## Folder Structure

```text
SmartVision-AI-Surveillance-Suite/
  api_gateway/                 FastAPI application entrypoint
  shared_core/
    ai_models/                 YOLO adapter and detector interfaces
    alert_engine/              Alert model and dispatcher
    configs/                   Shared defaults
    dashboard/                 REST/WebSocket dashboard routes
    database/                  SQLAlchemy models/repository/schema
    motion_engine/             Frame differencing and background subtraction
    notifications/             Email, Telegram, SMS, sound providers
    recording_engine/          Event recorder, circular buffer, retention
    stream_manager/            Thread-safe camera capture/manager
    tracking_engine/           Tracker abstraction and centroid fallback
    utils/                     Config, logging, GPU, geometry helpers
  highway_surveillance/        Fully working reference module
  traffic_management/          Independent starter module
  smart_city_security/         Independent starter module
  retail_analytics/            Independent starter module
  industrial_safety/           Independent starter module
  smart_parking/               Independent starter module
  railway_surveillance/        Independent starter module
  campus_security/             Independent starter module
  home_security/               Independent starter module
  wildlife_monitoring/         Independent starter module
  frontend/                    React monitoring dashboard
  scripts/                     Setup, sample generation, module runner
  benchmarks/                  Performance checks
  tests/                       Unit and API tests
```

Each domain module has its own `config.yaml`, `detector.py`, `pipeline.py`, `alerts.py`, `api.py`, `service.py`, `requirements.txt`, `logs/`, and `recordings/` folders.

## Quick Start

```powershell
cd C:\Btech_Projects\opencv_cctv\SmartVision-AI-Surveillance-Suite
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\create_sample_video.py
.\.venv\Scripts\uvicorn.exe api_gateway.main:app --reload
```

Open the API at `http://localhost:8000/api/health`.

Run the React dashboard:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Run A Module Independently

```powershell
python -m highway_surveillance.service
```

or:

```powershell
python scripts/run_module.py highway_surveillance
```

Enable a camera in that module's `config.yaml`. Sources can be `0`, a video file, an RTSP URL, or an IP camera URL.

## Event Recording Design

The recorder never writes continuous CCTV footage. It:

- buffers the last 3 to 5 seconds in memory,
- starts a clip only when motion and importance score cross thresholds,
- flushes the pre-event buffer into the event clip,
- keeps writing while motion remains active,
- stops after the configured idle timeout,
- saves snapshots for minor motion,
- writes timeline metadata next to every clip,
- supports OpenCV codecs such as `mp4v`, `H264`, `avc1`, and `HEVC`,
- can post-compress with ffmpeg through `shared_core.recording_engine.compression`,
- can prune old low-priority events through `shared_core.recording_engine.retention`.

## GPU Settings

Set these in `.env`:

```env
AI_DEVICE=auto
AI_HALF_PRECISION=true
```

`auto` uses CUDA when PyTorch reports it as available. For GPU deployments, install the CUDA-matched PyTorch wheel first, then install `requirements.txt`.

## REST Endpoints

- `GET /api/health`
- `GET /api/events`
- `GET /api/alerts`
- `GET /api/cameras`
- `GET /api/storage`
- `GET /api/analytics/summary`
- `GET /api/modules/{module}/health`
- `GET /api/modules/{module}/features`
- `GET /api/modules/{module}/events`
- `WS /api/ws/live/{camera_id}`
- `WS /api/ws/alerts`

Protected endpoints use the `x-api-key` header. The default development key is `dev-token`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The compose stack starts FastAPI, PostgreSQL, and the Vite dashboard.

## Tests And Benchmarks

```bash
pytest
python benchmarks/benchmark_motion.py
```

## Extending A Domain

1. Copy an existing module or rerun `scripts/scaffold_modules.py`.
2. Update `config.yaml` with cameras, model weights, zones, thresholds, and recording policy.
3. Implement domain-specific logic in `detector.py` and `pipeline.py`.
4. Register alerts in `alerts.py`.
5. Expose additional dashboard routes in `api.py`.

The shared core remains stable while each domain evolves as its own microservice-style unit.
