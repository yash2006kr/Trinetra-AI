# Home Security

Independent SmartVision AI service for `home_security`.

## Features

- human_detection
- pet_detection
- door_activity_monitoring
- intruder_alerts
- mobile_notification_system

## Run

```bash
python -m home_security.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
