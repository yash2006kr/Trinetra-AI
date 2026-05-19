# Smart Parking

Independent SmartVision AI service for `smart_parking`.

## Features

- empty_slot_detection
- parking_occupancy_analytics
- illegal_parking_alerts
- anpr_integration
- parking_duration_tracking

## Run

```bash
python -m smart_parking.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
