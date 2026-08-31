SENSOR_CONFIG = {
    "heart_rate": {
        "min": 60,
        "max": 100,
        "noise": 2,
    },
    "spo2": {
        "min": 95,
        "max": 100,
        "noise": 0.5,
    },
    "temperature": {
        "min": 36.1,
        "max": 37.5,
        "noise": 0.1,
    },
    "systolic_bp": {
        "min": 90,
        "max": 140,
        "noise": 3,
    },
    "diastolic_bp": {
        "min": 60,
        "max": 90,
        "noise": 2,
    },
}

DATA_FIELDS = [
    "patient_id",
    "timestamp",
    "heart_rate",
    "spo2",
    "temperature",
    "systolic_bp",
    "diastolic_bp",
    "activity",
    "fall_detected",
]