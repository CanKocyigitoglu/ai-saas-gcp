from scripts.cost_estimator import (
    DEFAULT_MONTHLY_HOURS,
    build_stage8_estimate,
    instances_required,
)


def test_instances_required_rounds_up():
    assert instances_required(users=100, capacity_per_instance=100) == 1
    assert instances_required(users=101, capacity_per_instance=100) == 2
    assert instances_required(users=100000, capacity_per_instance=5000) == 20


def test_instances_required_rejects_invalid_capacity():
    try:
        instances_required(users=100, capacity_per_instance=0)
    except ValueError as exc:
        assert "capacity_per_instance" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_stage8_estimate_total_cost():
    estimate = build_stage8_estimate(
        yolo_users=100,
        llm_users=100,
        worker_users=100000,
        yolo_capacity=100,
        llm_capacity=100,
        worker_capacity=5000,
        yolo_hourly_price=1.0,
        llm_hourly_price=1.0,
        worker_hourly_price=1.0,
        api_instances=1,
        api_hourly_price=1.0,
        rabbitmq_instances=1,
        rabbitmq_hourly_price=1.0,
        postgres_instances=1,
        postgres_hourly_price=1.0,
        disk_cost=10.0,
        network_cost=5.0,
        firebase_constant_f=3.0,
        monthly_hours=DEFAULT_MONTHLY_HOURS,
    )

    # 1 YOLO + 1 LLM + 20 workers + 1 API + 1 RabbitMQ + 1 PostgreSQL = 25 instances
    assert estimate.compute_cost == 25 * DEFAULT_MONTHLY_HOURS
    assert estimate.total_cost == (25 * DEFAULT_MONTHLY_HOURS) + 10.0 + 5.0 + 3.0
