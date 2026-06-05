import json
from typing import Any

from app.services.llm_client import generate_bitnet_response


def build_ecowaste_interpretation_prompt(
    original_output: dict[str, Any],
    processed_output: dict[str, Any],
) -> str:
    """
    Builds a grounded prompt for BitNet using YOLO detections and deterministic EcoWaste rules.
    The LLM should explain, not override, the structured rule-based recommendations.
    """
    compact_payload = {
        "filename": original_output.get("filename"),
        "model": original_output.get("model"),
        "num_predictions": original_output.get("num_predictions"),
        "predictions": original_output.get("predictions", []),
        "label_counts": processed_output.get("label_counts", {}),
        "ecowaste_recommendations": processed_output.get("ecowaste_recommendations", []),
    }

    return f"""
You are an EcoWaste sorting assistant.

Your task is to explain the waste-sorting result to a user in clear and practical language.

Use ONLY the detections and rule-based recommendations provided below.
Do not invent objects that are not detected.
Do not override the recommended_bin values.
If confidence is low or the label is "other_litter", mention that manual review is needed.

Return a concise explanation with:
1. A one-sentence scene summary.
2. A sorting recommendation for each detected item type.
3. Any uncertainty or manual-review warning.
4. One short sustainability tip.

Structured detection and recommendation data:
{json.dumps(compact_payload, indent=2)}
""".strip()


async def generate_ecowaste_interpretation(
    original_output: dict[str, Any],
    processed_output: dict[str, Any],
) -> str:
    prompt = build_ecowaste_interpretation_prompt(
        original_output=original_output,
        processed_output=processed_output,
    )

    return await generate_bitnet_response(prompt)
