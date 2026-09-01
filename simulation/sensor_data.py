from dataclasses import dataclass, asdict
import json


@dataclass
class SensorData:
    patient_id: str
    timestamp: float

    heart_rate: float
    spo2: float
    temperature: float

    systolic_bp: float
    diastolic_bp: float

    accel_x: float
    accel_y: float
    accel_z: float

    gyro_x: float
    gyro_y: float
    gyro_z: float

    activity: str
    fall_detected: bool
    event: str

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict())