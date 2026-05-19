# API

Set `SMARTVISION_API_KEY` in `.env` and pass it as `x-api-key`.

## Dashboard

- `GET /api/health`
- `GET /api/events?module=highway_surveillance&limit=100`
- `GET /api/alerts?limit=100`
- `GET /api/cameras`
- `GET /api/storage`
- `GET /api/analytics/summary`
- `GET /api/events/{event_id}/clip`

## WebSockets

- `/api/ws/live/{camera_id}` streams JPEG frames as base64 JSON.
- `/api/ws/alerts` streams recent alert batches.

## Modules

Every module exposes:

- `GET /api/modules/<module>/health`
- `GET /api/modules/<module>/features`
- `GET /api/modules/<module>/config`
- `GET /api/modules/<module>/events`
