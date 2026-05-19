# Smart City Security

Independent SmartVision AI service for `smart_city_security`.

## Features

- suspicious_activity_detection
- abandoned_object_detection
- crowd_density_analysis
- loitering_detection
- fight_detection
- weapon_detection
- intrusion_detection
- restricted_zone_monitoring

## Run

```bash
python -m smart_city_security.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
