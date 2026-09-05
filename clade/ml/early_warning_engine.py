from typing import Dict


def calculate_early_warning(probabilities: Dict[str, float]) -> Dict:
    """
    Convert early-warning model probabilities into a
    dashboard-friendly warning state.
    """

    if not probabilities:
        raise ValueError("Probabilities cannot be empty.")

    pre_fall_probability = float(
        probabilities.get("pre_fall", 0.0)
    )

    transition_probability = float(
        probabilities.get("fall_transition", 0.0)
    )

    fall_probability = float(
        probabilities.get("fall", 0.0)
    )

    post_fall_probability = float(
        probabilities.get("post_fall", 0.0)
    )

    normal_probability = float(
        probabilities.get("normal", 0.0)
    )

    # ---------------------------------------------------------
    # Determine warning state
    # ---------------------------------------------------------

    if fall_probability >= 0.50:
        warning_state = "CRITICAL"
        warning_type = "FALL_DETECTED"
        message = "Fall event detected."

    elif post_fall_probability >= 0.50:
        warning_state = "CRITICAL"
        warning_type = "POST_FALL"
        message = "Possible post-fall state detected."

    elif transition_probability >= 0.50:
        warning_state = "WARNING"
        warning_type = "FALL_IMMINENT"
        message = "Potential fall sequence detected."

    elif pre_fall_probability >= 0.50:
        warning_state = "WARNING"
        warning_type = "PRE_FALL"
        message = "Pre-fall motion pattern detected."

    else:
        warning_state = "NORMAL"
        warning_type = "NONE"
        message = "No immediate fall warning detected."

    # ---------------------------------------------------------
    # Find highest-probability state
    # ---------------------------------------------------------

    probabilities_copy = {
        "normal": normal_probability,
        "pre_fall": pre_fall_probability,
        "fall_transition": transition_probability,
        "fall": fall_probability,
        "post_fall": post_fall_probability,
    }

    predicted_state = max(
        probabilities_copy,
        key=probabilities_copy.get
    )

    confidence = probabilities_copy[predicted_state]

    # ---------------------------------------------------------
    # Dashboard-friendly result
    # ---------------------------------------------------------

    return {
        "warning_state": warning_state,
        "warning_type": warning_type,
        "predicted_state": predicted_state,
        "confidence": round(confidence * 100, 2),
        "pre_fall_probability": round(
            pre_fall_probability * 100,
            2
        ),
        "fall_transition_probability": round(
            transition_probability * 100,
            2
        ),
        "fall_probability": round(
            fall_probability * 100,
            2
        ),
        "post_fall_probability": round(
            post_fall_probability * 100,
            2
        ),
        "message": message,
    }


if __name__ == "__main__":

    # Example 1: normal state
    normal_example = {
        "normal": 0.98,
        "pre_fall": 0.01,
        "fall_transition": 0.005,
        "fall": 0.003,
        "post_fall": 0.002,
    }

    print("NORMAL EXAMPLE")
    print(calculate_early_warning(normal_example))

    print()

    # Example 2: pre-fall warning
    warning_example = {
        "normal": 0.05,
        "pre_fall": 0.90,
        "fall_transition": 0.04,
        "fall": 0.005,
        "post_fall": 0.005,
    }

    print("PRE-FALL EXAMPLE")
    print(calculate_early_warning(warning_example))

    print()

    # Example 3: fall detected
    fall_example = {
        "normal": 0.01,
        "pre_fall": 0.02,
        "fall_transition": 0.03,
        "fall": 0.93,
        "post_fall": 0.01,
    }

    print("FALL EXAMPLE")
    print(calculate_early_warning(fall_example))