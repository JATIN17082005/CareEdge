"""
CAREEDGE CLADE — Risk Engine

Converts ML event probabilities into:
- predicted event
- confidence
- risk score
- risk level
- explanation

This module is intentionally separate from the ML classifier so that
the classification model and clinical-risk logic can be changed independently.
"""

RISK_LEVELS = {
    "normal": "LOW",
    "tachycardia": "HIGH",
    "hypoxia": "HIGH",
    "fever": "MEDIUM",
    "hypertension": "MEDIUM",
    "fall": "CRITICAL",
}

RISK_SCORES = {
    "normal": 10,
    "fever": 50,
    "hypertension": 60,
    "tachycardia": 80,
    "hypoxia": 85,
    "fall": 100,
}

RISK_REASONS = {
    "normal": "No major abnormal event detected.",
    "fever": "Elevated temperature pattern detected.",
    "hypertension": "Elevated blood-pressure pattern detected.",
    "tachycardia": "Elevated heart-rate pattern detected.",
    "hypoxia": "Low oxygen-saturation pattern detected.",
    "fall": "Fall-like motion pattern detected.",
}


def calculate_risk(probabilities):
    """
    Convert model probabilities into a dashboard-ready risk result.

    Parameters
    ----------
    probabilities : dict
        Dictionary mapping event names to model probabilities.
        Example:
        {
            "normal": 0.02,
            "tachycardia": 0.01,
            "hypoxia": 0.03,
            "fever": 0.01,
            "hypertension": 0.02,
            "fall": 0.91
        }

    Returns
    -------
    dict
        Dashboard-ready risk information.
    """

    if not probabilities:
        raise ValueError("Probabilities cannot be empty.")

    # Highest-probability event becomes the predicted event
    predicted_event = max(
        probabilities,
        key=probabilities.get
    )

    confidence = float(probabilities[predicted_event])

    risk_level = RISK_LEVELS.get(
        predicted_event,
        "UNKNOWN"
    )

    base_score = RISK_SCORES.get(
        predicted_event,
        0
    )

    # Scale the event's base severity by model confidence.
    # Example:
    # fall with 100% confidence -> 100
    # fall with 50% confidence  -> 50
    risk_score = round(
        base_score * confidence,
        2
    )

    reason = RISK_REASONS.get(
        predicted_event,
        "Unrecognized event detected."
    )

    return {
        "predicted_event": predicted_event,
        "confidence": round(confidence * 100, 2),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason": reason,
        "probabilities": {
            event: round(float(probability) * 100, 2)
            for event, probability in probabilities.items()
        },
    }


if __name__ == "__main__":

    # Example 1: Fall
    fall_example = {
        "normal": 0.02,
        "tachycardia": 0.01,
        "hypoxia": 0.03,
        "fever": 0.01,
        "hypertension": 0.02,
        "fall": 0.91,
    }

    print("=" * 70)
    print("CAREEDGE CLADE — RISK ENGINE TEST")
    print("=" * 70)

    result = calculate_risk(fall_example)

    print()
    print("Predicted event :", result["predicted_event"])
    print("Confidence      :", f'{result["confidence"]}%')
    print("Risk score      :", result["risk_score"])
    print("Risk level      :", result["risk_level"])
    print("Reason          :", result["reason"])

    print()
    print("Probabilities:")
    for event, probability in result["probabilities"].items():
        print(f"  {event:15s}: {probability}%")