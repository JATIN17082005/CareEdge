import random


def apply_event(reading, event_name):
    updated = reading.copy()

    if event_name == "normal":
        updated["activity"] = "normal"
        updated["fall_detected"] = False

    elif event_name == "tachycardia":
        updated["heart_rate"] = random.randint(110, 140)
        updated["activity"] = "high"
        updated["fall_detected"] = False

    elif event_name == "hypoxia":
        updated["spo2"] = round(random.uniform(85, 92), 1)
        updated["activity"] = "low"
        updated["fall_detected"] = False

    elif event_name == "fever":
        updated["temperature"] = round(random.uniform(38.0, 39.5), 1)
        updated["activity"] = "low"
        updated["fall_detected"] = False

    elif event_name == "hypertension":
        updated["systolic_bp"] = random.randint(150, 180)
        updated["diastolic_bp"] = random.randint(95, 110)
        updated["activity"] = "normal"
        updated["fall_detected"] = False

    elif event_name == "fall":
        updated["activity"] = "inactive"
        updated["fall_detected"] = True

    else:
        raise ValueError(f"Unknown event: {event_name}")

    updated["event"] = event_name

    return updated