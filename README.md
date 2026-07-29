# Trinetra AI

Trinetra AI is an AI-powered CCTV surveillance suite built with Python, OpenCV, YOLO-compatible Ultralytics models, FastAPI, and a React monitoring dashboard.

The working application is in:

```text
SmartVision-AI-Surveillance-Suite/
```

## Demo Features

- Live webcam and RTSP/IP camera support
- OpenCV video capture and frame processing
- YOLO object detection with green and red bounding boxes
- Highway surveillance speed-limit warning demo
- FastAPI REST APIs and WebSocket live streaming
- React dashboard with live camera view, alerts, settings, model controls, analytics, and event panels
- Motion-triggered event recording architecture with pre-event buffering
- Modular surveillance domains for highway, traffic, city security, retail, industrial safety, parking, railway, campus, home, and wildlife use cases

## Run Locally

Open PowerShell from the repository root:

```powershell
cd SmartVision-AI-Surveillance-Suite
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn.exe api_gateway.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell terminal:

```powershell
cd SmartVision-AI-Surveillance-Suite\frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open the dashboard:

```text
http://127.0.0.1:5173
```

## What To Click In The Demo

1. Select `highway_surveillance` from the module list.
2. Use the webcam selector in the Live Video panel to choose your camera.
3. Keep `Detection ON` enabled to see OpenCV/YOLO annotated frames.
4. Green boxes are normal detections.
5. Red boxes indicate alert-worthy detections, such as speed-limit warnings in highway mode.
6. Click Settings to view API, camera, and storage status.
7. Click Model Controls to tune demo confidence and edge/recording switches.
8. Click Test Alert or Test Event to populate the alert and event panels for presentation.

## Detailed Documentation

Full architecture, module layout, API routes, Docker setup, recording design, and extension notes are documented in:

```text
SmartVision-AI-Surveillance-Suite/README.md
```
