# Railway Surveillance

Independent SmartVision AI service for `railway_surveillance`.

## Features

- track_intrusion_detection
- human_detection_on_tracks
- platform_crowd_analysis
- unattended_baggage_detection

## Run

```bash
python -m railway_surveillance.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
