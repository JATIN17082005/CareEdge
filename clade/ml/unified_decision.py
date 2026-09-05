from typing import Dict


def make_unified_decision(
    risk_result: Dict,
    early_warning_result: Dict,
) -> Dict:
    """
    Combine the main CLADE risk result and the
    early-warning result into one dashboard state.

    Priority:
        1. Confirmed/current fall
        2. Post-fall
        3. Fall transition
        4. Pre-fall warning
        5. Other medical risk
        6. Normal
    """

    warning_type = early_warning_result.get(
        "warning_type",
        "NONE",
    )

    predicted_event = risk_result.get(
        "predicted_event",
        "unknown",
    )

    # ---------------------------------------------------------
    # 1. Current fall
    # ---------------------------------------------------------

    if (
        warning_type == "FALL_DETECTED"
        or (
            predicted_event == "fall"
            and early_warning_result.get(
                "predicted_state"
            ) == "fall"
        )
    ):

        return {
            "state": "CRITICAL",
            "alert_type": "FALL_DETECTED",
            "priority": 1,
            "message": "Fall event detected.",
            "action": "Immediate attention required.",
            "confidence": risk_result.get(
                "confidence",
                0,
            ),
        }

    # ---------------------------------------------------------
    # 2. Post-fall
    # ---------------------------------------------------------

    if warning_type == "POST_FALL":

        return {
            "state": "CRITICAL",
            "alert_type": "POST_FALL",
            "priority": 2,
            "message": "Possible post-fall state detected.",
            "action": "Check patient immediately.",
            "confidence": early_warning_result.get(
                "confidence",
                0,
            ),
        }

    # ---------------------------------------------------------
    # 3. Fall transition
    # ---------------------------------------------------------

    if warning_type == "FALL_IMMINENT":

        return {
            "state": "WARNING",
            "alert_type": "FALL_IMMINENT",
            "priority": 3,
            "message": "Potential fall sequence detected.",
            "action": "Monitor patient closely.",
            "confidence": early_warning_result.get(
                "confidence",
                0,
            ),
        }

    # ---------------------------------------------------------
    # 4. Pre-fall
    # ---------------------------------------------------------

    if warning_type == "PRE_FALL":

        return {
            "state": "WARNING",
            "alert_type": "PRE_FALL",
            "priority": 4,
            "message": "Pre-fall motion pattern detected.",
            "action": "Monitor patient closely.",
            "confidence": early_warning_result.get(
                "confidence",
                0,
            ),
        }

    # ---------------------------------------------------------
    # 5. Other medical risk
    # ---------------------------------------------------------

    risk_level = risk_result.get(
        "risk_level",
        "UNKNOWN",
    )

    if risk_level in [
        "HIGH",
        "MEDIUM",
    ]:

        return {
            "state": risk_level,
            "alert_type": predicted_event.upper(),
            "priority": 5,
            "message": risk_result.get(
                "reason",
                "Abnormal physiological pattern detected.",
            ),
            "action": "Review patient vitals.",
            "confidence": risk_result.get(
                "confidence",
                0,
            ),
        }

    # ---------------------------------------------------------
    # 6. Normal
    # ---------------------------------------------------------

    return {
        "state": "NORMAL",
        "alert_type": "NONE",
        "priority": 6,
        "message": "No immediate risk detected.",
        "action": "Continue monitoring.",
        "confidence": risk_result.get(
            "confidence",
            0,
        ),
    }


# =============================================================
# DEMO
# =============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("CAREEDGE — UNIFIED CLADE DECISION ENGINE")
    print("=" * 70)

    # ---------------------------------------------------------
    # Example 1 — Pre-fall
    # ---------------------------------------------------------

    risk = {
        "predicted_event": "fall",
        "confidence": 99.33,
        "risk_level": "CRITICAL",
        "reason": "Fall-like motion pattern detected.",
    }

    early_warning = {
        "warning_state": "WARNING",
        "warning_type": "PRE_FALL",
        "predicted_state": "pre_fall",
        "confidence": 100.0,
    }

    result = make_unified_decision(
        risk,
        early_warning,
    )

    print()
    print("PRE-FALL SCENARIO")
    print(result)

    # ---------------------------------------------------------
    # Example 2 — Confirmed fall
    # ---------------------------------------------------------

    risk = {
        "predicted_event": "fall",
        "confidence": 99.8,
        "risk_level": "CRITICAL",
        "reason": "Fall-like motion pattern detected.",
    }

    early_warning = {
        "warning_state": "CRITICAL",
        "warning_type": "FALL_DETECTED",
        "predicted_state": "fall",
        "confidence": 99.8,
    }

    result = make_unified_decision(
        risk,
        early_warning,
    )

    print()
    print("FALL SCENARIO")
    print(result)

    # ---------------------------------------------------------
    # Example 3 — Normal
    # ---------------------------------------------------------

    risk = {
        "predicted_event": "normal",
        "confidence": 98.0,
        "risk_level": "LOW",
        "reason": "No major abnormal event detected.",
    }

    early_warning = {
        "warning_state": "NORMAL",
        "warning_type": "NONE",
        "predicted_state": "normal",
        "confidence": 98.0,
    }

    result = make_unified_decision(
        risk,
        early_warning,
    )

    print()
    print("NORMAL SCENARIO")
    print(result)

    print()
    print("=" * 70)
    print("UNIFIED DECISION ENGINE COMPLETE")
    print("=" * 70)