# Deployment

## Local Edge Device

Use `.env` with SQLite:

```env
DATABASE_URL=sqlite:///data/smartvision.db
AI_DEVICE=auto
```

Run one module:

```bash
python -m highway_surveillance.service
```

Run the API:

```bash
uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000
```

## Docker Compose

```bash
docker compose up --build
```

## GPU Containers

Use an NVIDIA runtime base image, install the CUDA-matched PyTorch wheel, and set:

```env
AI_DEVICE=cuda:0
AI_HALF_PRECISION=true
```

## Cloud Readiness

The suite is ready for:

- PostgreSQL metadata storage.
- Object-storage clip archival.
- One container per module.
- Horizontal FastAPI dashboard replicas.
- Edge-to-cloud event synchronization.
