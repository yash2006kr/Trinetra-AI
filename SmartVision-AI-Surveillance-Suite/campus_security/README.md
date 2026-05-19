# Campus Security

Independent SmartVision AI service for `campus_security`.

## Features

- face_recognition_attendance
- unauthorized_entry_detection
- hostel_corridor_monitoring
- night_activity_detection

## Run

```bash
python -m campus_security.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
