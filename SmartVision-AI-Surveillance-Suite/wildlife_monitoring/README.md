# Wildlife Monitoring

Independent SmartVision AI service for `wildlife_monitoring`.

## Features

- animal_classification
- poacher_detection
- forest_fire_smoke_alerts
- zone_intrusion_alerts

## Run

```bash
python -m wildlife_monitoring.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
