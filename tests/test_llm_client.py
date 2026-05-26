import asyncio

import httpx
import pytest

from app.services import llm_client


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json):
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "This is a BitNet response."
                        }
                    }
                ]
            }
        )


class BadFormatAsyncClient(FakeAsyncClient):
    async def post(self, url, json):
        return FakeResponse({"unexpected": "format"})


class FailingAsyncClient(FakeAsyncClient):
    async def post(self, url, json):
        raise httpx.ConnectError("connection failed")


def test_generate_bitnet_response_success(monkeypatch):
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(llm_client.generate_bitnet_response("hello"))

    assert result == "This is a BitNet response."


def test_generate_bitnet_response_handles_http_error(monkeypatch):
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FailingAsyncClient)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(llm_client.generate_bitnet_response("hello"))

    assert "BitNet service request failed" in str(exc_info.value)


def test_generate_bitnet_response_handles_unexpected_format(monkeypatch):
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", BadFormatAsyncClient)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(llm_client.generate_bitnet_response("hello"))

    assert "Unexpected BitNet response format" in str(exc_info.value)
