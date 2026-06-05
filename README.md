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

## Security notes

- Firebase Authentication protects the business endpoints.
- Firestore access uses GCP Application Default Credentials and IAM.
- Internal services are bound to `127.0.0.1`.
- API security headers are enabled.
- CORS and trusted hosts are configurable.
- Request size limits and upload content-type validation are enforced.
- A lightweight rate limiter is enabled.
- Sensitive local files are excluded from Git.
- The API/worker image runs as a non-root user.

See `docs/security.md` for details.

## Product scenario: EcoWaste Sorting Assistant

This project is now positioned as **EcoWaste Sorting Assistant**, a cloud-based AI SaaS prototype for waste-object detection and recycling guidance.

The system uses a custom YOLO model trained on TACO-style waste classes through `models/yolo/best.pt`. Users upload a waste image, receive object detections, and the RabbitMQ post-processing worker produces sorting recommendations such as recyclable plastic, paper/cardboard, metal, soft plastic, general waste, or manual review.

See `docs/product_scenario.md` for the full product scenario.
