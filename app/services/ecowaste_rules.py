from typing import Any


def _normalise_label(label: str) -> str:
    return label.lower().strip().replace(" ", "_").replace("-", "_")


ECO_WASTE_RULES: dict[str, dict[str, str]] = {
    "plastic_bag_wrapper": {
        "waste_category": "soft_plastic",
        "recommended_bin": "soft plastics / specialist recycling if available",
        "handling_note": "Check local recycling rules; soft plastic is often collected separately.",
    },
    "bottle_or_cap": {
        "waste_category": "plastic_or_metal_recyclable",
        "recommended_bin": "recycling bin",
        "handling_note": "Empty and rinse bottles or caps before recycling when possible.",
    },
    "can": {
        "waste_category": "metal_recyclable",
        "recommended_bin": "metal recycling bin",
        "handling_note": "Empty and rinse cans before recycling.",
    },
    "paper_or_carton": {
        "waste_category": "paper_cardboard",
        "recommended_bin": "paper/cardboard recycling bin",
        "handling_note": "Keep paper and carton dry and clean.",
    },
    "plastic_container": {
        "waste_category": "rigid_plastic",
        "recommended_bin": "plastic recycling bin",
        "handling_note": "Empty and rinse containers before recycling.",
    },
    "cup": {
        "waste_category": "mixed_material",
        "recommended_bin": "check material / general waste if contaminated",
        "handling_note": "Disposable cups may contain plastic lining; check local rules.",
    },
    "foam_or_styrofoam": {
        "waste_category": "foam_styrofoam",
        "recommended_bin": "general waste or specialist recycling",
        "handling_note": "Styrofoam is often not accepted in standard recycling streams.",
    },
    "glass": {
        "waste_category": "glass",
        "recommended_bin": "glass recycling bin",
        "handling_note": "Handle broken glass carefully.",
    },
    "battery": {
        "waste_category": "hazardous",
        "recommended_bin": "battery/e-waste collection point",
        "handling_note": "Do not place batteries in normal bins.",
    },
    "cigarette": {
        "waste_category": "general_litter",
        "recommended_bin": "general waste",
        "handling_note": "Cigarette waste is contaminated and should not enter recycling.",
    },
    "other_litter": {
        "waste_category": "unknown_or_mixed",
        "recommended_bin": "manual review",
        "handling_note": "The object needs manual checking before disposal.",
    },
}


ALIASES: dict[str, str] = {
    "plastic_bag": "plastic_bag_wrapper",
    "wrapper": "plastic_bag_wrapper",
    "bottle": "bottle_or_cap",
    "bottle_cap": "bottle_or_cap",
    "paper": "paper_or_carton",
    "carton": "paper_or_carton",
    "plastic": "plastic_container",
    "plastic_container": "plastic_container",
    "styrofoam": "foam_or_styrofoam",
    "foam": "foam_or_styrofoam",
    "aluminium_can": "can",
    "metal_can": "can",
}


def classify_waste_label(label: str) -> dict[str, str]:
    normalised = _normalise_label(label)
    canonical = ALIASES.get(normalised, normalised)

    return ECO_WASTE_RULES.get(
        canonical,
        {
            "waste_category": "unknown",
            "recommended_bin": "manual review",
            "handling_note": "No rule exists for this detected class yet.",
        },
    )


def build_ecowaste_recommendations(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations = []

    for prediction in predictions:
        label = str(prediction.get("label", "unknown"))
        confidence = float(prediction.get("confidence", 0.0))
        rule = classify_waste_label(label)

        recommendations.append(
            {
                "label": label,
                "confidence": confidence,
                "waste_category": rule["waste_category"],
                "recommended_bin": rule["recommended_bin"],
                "handling_note": rule["handling_note"],
                "bbox": prediction.get("bbox"),
            }
        )

    return recommendations
