# Stage 9 — Monitoring

This project uses Prometheus and Grafana for monitoring.

## Components

- FastAPI exposes Prometheus metrics at `/metrics`.
- Prometheus scrapes the FastAPI service.
- Grafana visualises request rate, latency, errors, and total requests.

## Local endpoints

When running inside the GCP VM:

```text
FastAPI:    http://localhost:8000
Metrics:    http://localhost:8000/metrics
Prometheus: http://localhost:9090
Grafana:    http://localhost:3000
