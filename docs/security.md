# Stage 11 — Security Hardening

This stage protects the API, database, storage, and internal services.

## Implemented protections

### 1. Firebase Authentication

All business endpoints are protected with Firebase ID token authentication.

Protected endpoints include:

- `/api/v1/text/generate`
- `/api/v1/image/predict`
- `/api/v1/history`
- `/api/v1/firebase/outputs`
- `/api/v1/postprocess/results`

Public endpoints are limited to:

- `/health`
- `/metrics`
- `/docs`
- `/openapi.json`

### 2. Firestore security

Firestore is accessed from the backend through Firebase Admin SDK and Google Application Default Credentials on the GCP VM.

No Firebase private key file is committed to the repository.

### 3. IAM-based access

The VM service account is used for Firestore access. Access is controlled through IAM, not hardcoded service account JSON keys.

### 4. Local-only service exposure

Docker Compose binds service ports to `127.0.0.1`, preventing public exposure of internal services.

Examples:

```text
127.0.0.1:8000  -> FastAPI
127.0.0.1:5432  -> PostgreSQL
127.0.0.1:5672  -> RabbitMQ
127.0.0.1:15672 -> RabbitMQ UI
127.0.0.1:9090  -> Prometheus
127.0.0.1:3000  -> Grafana
