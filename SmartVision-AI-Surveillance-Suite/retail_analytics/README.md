# Retail Analytics

Independent SmartVision AI service for `retail_analytics`.

## Features

- customer_counting
- heatmap_generation
- queue_analysis
- shelf_monitoring
- theft_detection
- customer_movement_tracking
- staff_activity_analysis

## Run

```bash
python -m retail_analytics.service
```

The module uses its local `config.yaml`, writes logs under `logs/`, and stores
event clips/snapshots under `recordings/`.
