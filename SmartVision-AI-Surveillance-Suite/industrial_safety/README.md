# Industrial Safety

Independent SmartVision AI service for `industrial_safety`.

## Features

- ppe_detection
- fire_smoke_detection
- worker_fall_detection
- unsafe_zone_alerts
- machine_proximity_alerts
- hazard_monitoring

## Run

```bash
python -m industrial_safety.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
