# EcoWaste Sorting Assistant — Product Scenario

## Product idea

EcoWaste Sorting Assistant is a cloud-based AI SaaS prototype that helps users identify waste objects in images and receive recycling or disposal recommendations.

## Target users

- Smart recycling stations
- Local clean-up initiatives
- Sustainability teams

## User journey

1. The user logs in with Firebase Authentication.
2. The user uploads a photo of waste items.
3. The custom YOLO model detects waste objects.
4. The API returns object labels, confidence scores, and bounding boxes.
5. The raw interaction is saved to PostgreSQL.
6. The model output is saved to Firebase Firestore.
7. RabbitMQ sends the output to a post-processing worker.
8. The worker generates EcoWaste sorting recommendations.
9. The processed result is saved to Firestore.
10. Prometheus and Grafana monitor the system.

## Input

Image file:

```text
JPEG, PNG, or WEBP waste image
