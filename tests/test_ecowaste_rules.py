from app.services.ecowaste_rules import build_ecowaste_recommendations, classify_waste_label


def test_classify_known_ecowaste_label():
    result = classify_waste_label("plastic_bag_wrapper")

    assert result["waste_category"] == "soft_plastic"
    assert "specialist" in result["recommended_bin"]


def test_classify_alias_label():
    result = classify_waste_label("bottle")

    assert result["waste_category"] == "plastic_or_metal_recyclable"


def test_build_ecowaste_recommendations():
    recommendations = build_ecowaste_recommendations(
        [
            {
                "label": "can",
                "confidence": 0.93,
                "bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
            }
        ]
    )

    assert recommendations[0]["label"] == "can"
    assert recommendations[0]["waste_category"] == "metal_recyclable"
    assert recommendations[0]["recommended_bin"] == "metal recycling bin"
