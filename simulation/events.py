import random


EVENTS = {
    "normal": {
        "description": "Stable physiological state",
    },
    "tachycardia": {
        "description": "Abnormally elevated heart rate",
    },
    "hypoxia": {
        "description": "Low oxygen saturation",
    },
    "fever": {
        "description": "Elevated body temperature",
    },
    "hypertension": {
        "description": "Elevated blood pressure",
    },
    "fall": {
        "description": "Possible patient fall detected",
    },
}


ACTIVITIES = [
    "sitting",
    "standing",
    "walking",
]


def random_activity():
    return random.choice(ACTIVITIES)


def apply_event(reading, event_name):
    updated = reading.copy()

    updated["activity"] = random_activity()
    updated["fall_detected"] = False

    if event_name == "normal":
        pass

    elif event_name == "tachycardia":
        updated["heart_rate"] = random.randint(110, 140)

    elif event_name == "hypoxia":
        updated["spo2"] = round(random.uniform(85, 92), 1)

    elif event_name == "fever":
        updated["temperature"] = round(random.uniform(38.0, 39.5), 1)

    elif event_name == "hypertension":
        updated["systolic_bp"] = random.randint(150, 180)
        updated["diastolic_bp"] = random.randint(95, 110)

    elif event_name == "fall":
        updated["fall_detected"] = True

    else:
        raise ValueError(f"Unknown event: {event_name}")

    updated["event"] = event_name

    return updated