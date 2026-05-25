import json
import os
import time
from typing import Any

import pika

from app.services.firebase_store import save_postprocessed_output
from app.services.postprocess import postprocess_model_output


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://ai_user:ai_password@rabbitmq:5672/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "postprocess_jobs")


def process_message(message: dict[str, Any]) -> dict[str, Any]:
    request_type = message["request_type"]
    original_output = message["output"]

    processed_output = postprocess_model_output(
        request_type=request_type,
        output=original_output,
    )

    saved = save_postprocessed_output(
        job_id=message["job_id"],
        request_type=request_type,
        input_summary=message.get("input_summary"),
        model=message.get("model"),
        firebase_output_id=message.get("firebase_output_id"),
        source_interaction_id=message.get("source_interaction_id"),
        original_output=original_output,
        processed_output=processed_output,
        metadata={
            "worker": "postprocess-worker",
            "queue": RABBITMQ_QUEUE,
        },
    )

    return saved


def callback(channel, method, properties, body):
    try:
        message = json.loads(body.decode("utf-8"))
        job_id = message.get("job_id", "unknown")

        print(f"[worker] Received job: {job_id}", flush=True)

        saved = process_message(message)

        print(f"[worker] Saved postprocessed result: {saved.get('id')}", flush=True)

        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as exc:
        print(f"[worker] Failed to process message: {exc}", flush=True)

        # Requeue false avoids infinite poison-message loops during development.
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    while True:
        try:
            print("[worker] Connecting to RabbitMQ...", flush=True)

            parameters = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=callback,
            )

            print(f"[worker] Waiting for jobs on queue: {RABBITMQ_QUEUE}", flush=True)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as exc:
            print(f"[worker] RabbitMQ connection failed: {exc}. Retrying in 5 seconds...", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
