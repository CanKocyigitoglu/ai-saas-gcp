import os
from typing import Any

import httpx


BITNET_BASE_URL = os.getenv("BITNET_BASE_URL", "http://bitnet:8080")
BITNET_MODEL_NAME = os.getenv("BITNET_MODEL_NAME", "microsoft/bitnet-b1.58-2B-4T")
BITNET_TIMEOUT_SECONDS = float(os.getenv("BITNET_TIMEOUT_SECONDS", "180"))


async def generate_bitnet_response(prompt: str) -> str:
    """
    Calls the BitNet/llama-server OpenAI-compatible chat completion endpoint.
    """
    url = f"{BITNET_BASE_URL.rstrip('/')}/v1/chat/completions"

    payload: dict[str, Any] = {
        "model": BITNET_MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise assistant inside an AI SaaS prototype.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.7,
        "max_tokens": 128,
    }

    try:
        async with httpx.AsyncClient(timeout=BITNET_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"BitNet service request failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected BitNet response format: {data}") from exc
