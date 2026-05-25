from __future__ import annotations

import argparse
from dataclasses import dataclass
from math import ceil


DEFAULT_MONTHLY_HOURS = 730


@dataclass
class ServiceCost:
    name: str
    users: int
    capacity_per_instance: int
    instances: int
    hourly_price_per_instance: float
    monthly_compute_cost: float


@dataclass
class CostEstimate:
    monthly_hours: int
    services: list[ServiceCost]
    disk_cost: float
    network_cost: float
    firebase_constant_f: float

    @property
    def compute_cost(self) -> float:
        return sum(service.monthly_compute_cost for service in self.services)

    @property
    def total_cost(self) -> float:
        return self.compute_cost + self.disk_cost + self.network_cost + self.firebase_constant_f


def instances_required(users: int, capacity_per_instance: int) -> int:
    if users < 0:
        raise ValueError("users must be non-negative")

    if capacity_per_instance <= 0:
        raise ValueError("capacity_per_instance must be greater than zero")

    if users == 0:
        return 0

    return ceil(users / capacity_per_instance)


def monthly_compute_cost(
    users: int,
    capacity_per_instance: int,
    hourly_price_per_instance: float,
    monthly_hours: int = DEFAULT_MONTHLY_HOURS,
) -> tuple[int, float]:
    instances = instances_required(users, capacity_per_instance)
    cost = instances * hourly_price_per_instance * monthly_hours
    return instances, cost


def build_stage8_estimate(
    yolo_users: int,
    llm_users: int,
    worker_users: int,
    yolo_capacity: int,
    llm_capacity: int,
    worker_capacity: int,
    yolo_hourly_price: float,
    llm_hourly_price: float,
    worker_hourly_price: float,
    api_instances: int,
    api_hourly_price: float,
    rabbitmq_instances: int,
    rabbitmq_hourly_price: float,
    postgres_instances: int,
    postgres_hourly_price: float,
    disk_cost: float,
    network_cost: float,
    firebase_constant_f: float,
    monthly_hours: int = DEFAULT_MONTHLY_HOURS,
) -> CostEstimate:
    services: list[ServiceCost] = []

    yolo_instances, yolo_cost = monthly_compute_cost(
        users=yolo_users,
        capacity_per_instance=yolo_capacity,
        hourly_price_per_instance=yolo_hourly_price,
        monthly_hours=monthly_hours,
    )
    services.append(
        ServiceCost(
            name="YOLO image service",
            users=yolo_users,
            capacity_per_instance=yolo_capacity,
            instances=yolo_instances,
            hourly_price_per_instance=yolo_hourly_price,
            monthly_compute_cost=yolo_cost,
        )
    )

    llm_instances, llm_cost = monthly_compute_cost(
        users=llm_users,
        capacity_per_instance=llm_capacity,
        hourly_price_per_instance=llm_hourly_price,
        monthly_hours=monthly_hours,
    )
    services.append(
        ServiceCost(
            name="BitNet LLM service",
            users=llm_users,
            capacity_per_instance=llm_capacity,
            instances=llm_instances,
            hourly_price_per_instance=llm_hourly_price,
            monthly_compute_cost=llm_cost,
        )
    )

    worker_instances, worker_cost = monthly_compute_cost(
        users=worker_users,
        capacity_per_instance=worker_capacity,
        hourly_price_per_instance=worker_hourly_price,
        monthly_hours=monthly_hours,
    )
    services.append(
        ServiceCost(
            name="RabbitMQ post-processing workers",
            users=worker_users,
            capacity_per_instance=worker_capacity,
            instances=worker_instances,
            hourly_price_per_instance=worker_hourly_price,
            monthly_compute_cost=worker_cost,
        )
    )

    services.append(
        ServiceCost(
            name="FastAPI gateway",
            users=0,
            capacity_per_instance=0,
            instances=api_instances,
            hourly_price_per_instance=api_hourly_price,
            monthly_compute_cost=api_instances * api_hourly_price * monthly_hours,
        )
    )

    services.append(
        ServiceCost(
            name="RabbitMQ broker",
            users=0,
            capacity_per_instance=0,
            instances=rabbitmq_instances,
            hourly_price_per_instance=rabbitmq_hourly_price,
            monthly_compute_cost=rabbitmq_instances * rabbitmq_hourly_price * monthly_hours,
        )
    )

    services.append(
        ServiceCost(
            name="PostgreSQL request-history service",
            users=0,
            capacity_per_instance=0,
            instances=postgres_instances,
            hourly_price_per_instance=postgres_hourly_price,
            monthly_compute_cost=postgres_instances * postgres_hourly_price * monthly_hours,
        )
    )

    return CostEstimate(
        monthly_hours=monthly_hours,
        services=services,
        disk_cost=disk_cost,
        network_cost=network_cost,
        firebase_constant_f=firebase_constant_f,
    )


def print_estimate(estimate: CostEstimate) -> None:
    print("Stage 8 Infrastructure Cost Estimate")
    print("=" * 42)
    print(f"Monthly hours: {estimate.monthly_hours}")
    print()

    header = f"{'Service':35} {'Users':>10} {'Capacity':>10} {'Instances':>10} {'$/h':>10} {'$/month':>12}"
    print(header)
    print("-" * len(header))

    for service in estimate.services:
        users = "-" if service.users == 0 else str(service.users)
        capacity = "-" if service.capacity_per_instance == 0 else str(service.capacity_per_instance)

        print(
            f"{service.name:35} "
            f"{users:>10} "
            f"{capacity:>10} "
            f"{service.instances:>10} "
            f"{service.hourly_price_per_instance:>10.4f} "
            f"{service.monthly_compute_cost:>12.2f}"
        )

    print("-" * len(header))
    print(f"{'Compute subtotal':68} {estimate.compute_cost:>12.2f}")
    print(f"{'Disk cost':68} {estimate.disk_cost:>12.2f}")
    print(f"{'Network cost':68} {estimate.network_cost:>12.2f}")
    print(f"{'Firebase constant F':68} {estimate.firebase_constant_f:>12.2f}")
    print("=" * len(header))
    print(f"{'Estimated monthly total':68} {estimate.total_cost:>12.2f}")
    print()

    print("Core formula:")
    print(
        "Total = H * Σ(instances_i * hourly_price_i) + Disk + Network + F"
    )
    print(
        "instances_i = ceil(users_i / capacity_per_instance_i)"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 8 cost estimator for the AI SaaS project.")

    parser.add_argument("--monthly-hours", type=int, default=DEFAULT_MONTHLY_HOURS)

    parser.add_argument("--yolo-users", type=int, default=100)
    parser.add_argument("--llm-users", type=int, default=100)
    parser.add_argument("--worker-users", type=int, default=100000)

    parser.add_argument("--yolo-capacity", type=int, default=100)
    parser.add_argument("--llm-capacity", type=int, default=100)
    parser.add_argument("--worker-capacity", type=int, default=5000)

    parser.add_argument("--yolo-hourly-price", type=float, default=0.134)
    parser.add_argument("--llm-hourly-price", type=float, default=0.134)
    parser.add_argument("--worker-hourly-price", type=float, default=0.134)

    parser.add_argument("--api-instances", type=int, default=1)
    parser.add_argument("--api-hourly-price", type=float, default=0.067)

    parser.add_argument("--rabbitmq-instances", type=int, default=1)
    parser.add_argument("--rabbitmq-hourly-price", type=float, default=0.067)

    parser.add_argument("--postgres-instances", type=int, default=1)
    parser.add_argument("--postgres-hourly-price", type=float, default=0.067)

    parser.add_argument("--disk-cost", type=float, default=0.0)
    parser.add_argument("--network-cost", type=float, default=0.0)
    parser.add_argument("--firebase-f-cost", type=float, default=0.0)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    estimate = build_stage8_estimate(
        yolo_users=args.yolo_users,
        llm_users=args.llm_users,
        worker_users=args.worker_users,
        yolo_capacity=args.yolo_capacity,
        llm_capacity=args.llm_capacity,
        worker_capacity=args.worker_capacity,
        yolo_hourly_price=args.yolo_hourly_price,
        llm_hourly_price=args.llm_hourly_price,
        worker_hourly_price=args.worker_hourly_price,
        api_instances=args.api_instances,
        api_hourly_price=args.api_hourly_price,
        rabbitmq_instances=args.rabbitmq_instances,
        rabbitmq_hourly_price=args.rabbitmq_hourly_price,
        postgres_instances=args.postgres_instances,
        postgres_hourly_price=args.postgres_hourly_price,
        disk_cost=args.disk_cost,
        network_cost=args.network_cost,
        firebase_constant_f=args.firebase_f_cost,
        monthly_hours=args.monthly_hours,
    )

    print_estimate(estimate)


if __name__ == "__main__":
    main()
