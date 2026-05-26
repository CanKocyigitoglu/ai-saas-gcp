import json

from app.services import rabbitmq_client


class FakeChannel:
    def __init__(self):
        self.declared = []
        self.published = []

    def queue_declare(self, queue, durable):
        self.declared.append({"queue": queue, "durable": durable})

    def basic_publish(self, exchange, routing_key, body, properties):
        self.published.append(
            {
                "exchange": exchange,
                "routing_key": routing_key,
                "body": body,
                "properties": properties,
            }
        )


class FakeConnection:
    def __init__(self, params):
        self.params = params
        self.channel_obj = FakeChannel()
        self.closed = False

    def channel(self):
        return self.channel_obj

    def close(self):
        self.closed = True


def test_publish_postprocess_job_sends_persistent_message(monkeypatch):
    created_connections = []

    def fake_blocking_connection(params):
        connection = FakeConnection(params)
        created_connections.append(connection)
        return connection

    monkeypatch.setattr(rabbitmq_client.pika, "BlockingConnection", fake_blocking_connection)
    monkeypatch.setattr(rabbitmq_client, "RABBITMQ_QUEUE", "test_jobs")

    job_id = rabbitmq_client.publish_postprocess_job(
        request_type="text",
        output={"output": "hello"},
        model="bitnet",
        input_summary="hello prompt",
        firebase_output_id="firebase-1",
        source_interaction_id=123,
    )

    assert job_id
    assert len(created_connections) == 1

    channel = created_connections[0].channel_obj
    assert channel.declared == [{"queue": "test_jobs", "durable": True}]
    assert len(channel.published) == 1
    assert channel.published[0]["routing_key"] == "test_jobs"

    body = json.loads(channel.published[0]["body"].decode("utf-8"))
    assert body["job_id"] == job_id
    assert body["request_type"] == "text"
    assert body["model"] == "bitnet"
    assert body["firebase_output_id"] == "firebase-1"
    assert created_connections[0].closed is True
