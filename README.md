# AI SaaS on GCP

This project is a FastAPI-based AI SaaS prototype designed to run on a Debian 12 VM using Docker and Docker Compose.

The current version contains placeholder services for:

- Image inference with YOLO11n
- Text inference with Microsoft BitNet

Future versions will add real model inference, database persistence, RabbitMQ-based post-processing, Firebase integration, authentication, monitoring, and security controls.

## Requirements

- Debian 12
- Docker
- Docker Compose plugin

## Build

```bash
docker compose build
