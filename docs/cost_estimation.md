# Stage 8 — Infrastructure Cost Estimation

## Purpose

This document estimates the infrastructure cost of the AI SaaS system under the Stage 8 assumptions:

- The YOLO image service serves 100 users.
- The BitNet LLM service serves 100 users.
- The RabbitMQ-based post-processing service scales to 100,000 users.
- Firebase storage is treated as a constant cost, represented as **F**.

The deployed system currently consists of:

- FastAPI gateway
- YOLO11n image inference service
- BitNet LLM service
- PostgreSQL request-history service
- Firebase Firestore output storage
- RabbitMQ message broker
- Post-processing worker service

## Why this is an estimate

Cloud prices vary by region, machine type, storage type, network usage, discounts, and billing account settings. Therefore, the calculation is expressed with formulas and configurable variables. The script `scripts/cost_estimator.py` can be used to replace the example prices with current Google Cloud prices.

## Variables

| Symbol | Meaning |
|---|---|
| H | Number of hours per month, default 730 |
| U_yolo | Number of YOLO users |
| U_llm | Number of BitNet LLM users |
| U_worker | Number of RabbitMQ/post-processing users |
| C_yolo | Users supported per YOLO service instance |
| C_llm | Users supported per LLM service instance |
| C_worker | Users supported per worker instance |
| P_yolo | Hourly price of one YOLO service instance |
| P_llm | Hourly price of one LLM service instance |
| P_worker | Hourly price of one post-processing worker instance |
| P_api | Hourly price of one FastAPI gateway instance |
| P_rabbitmq | Hourly price of one RabbitMQ broker instance |
| P_postgres | Hourly price of one PostgreSQL instance |
| D | Disk cost |
| N | Network cost |
| F | Firebase storage/read/write cost treated as a constant |

## Instance count formulas

```text
N_yolo = ceil(U_yolo / C_yolo)
N_llm = ceil(U_llm / C_llm)
N_worker = ceil(U_worker / C_worker)
