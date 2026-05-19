# Highway Surveillance

Fully working reference SmartVision module for highways.

## Capabilities

- Motion-triggered recording with 4 second pre-event buffering.
- Vehicle and person detection through YOLOv8/YOLOv11 compatible weights.
- Tracking-aware speed estimation with configurable pixel-to-meter scale.
- Speed-limit, wrong-way, lane-zone, emergency-vehicle, and illegal-parking alerts.
- Night-vision contrast optimization before inference.
- Independent REST API under `/api/modules/highway_surveillance`.

## Run

```bash
python -m highway_surveillance.service
```

Set `highway_demo.enabled: true` in `config.yaml` after generating or providing
`sample_datasets/highway_demo.mp4`, or replace the source with a webcam index or
RTSP URL.
