import random

from simulation.sensor_config import SENSOR_CONFIG


class SensorSimulator:
    def __init__(self, patient):
        self.patient = patient

    def _add_noise(self, value, noise):
        return value + random.uniform(-noise, noise)

    def read(self):
        return {
            "patient_id": self.patient.patient_id,
            "heart_rate": round(
                self._add_noise(
                    self.patient.heart_rate,
                    SENSOR_CONFIG["heart_rate"]["noise"],
                )
            ),
            "spo2": round(
                self._add_noise(
                    self.patient.spo2,
                    SENSOR_CONFIG["spo2"]["noise"],
                ),
                1,
            ),
            "temperature": round(
                self._add_noise(
                    self.patient.temperature,
                    SENSOR_CONFIG["temperature"]["noise"],
                ),
                1,
            ),
            "systolic_bp": round(
                self._add_noise(
                    self.patient.systolic_bp,
                    SENSOR_CONFIG["systolic_bp"]["noise"],
                )
            ),
            "diastolic_bp": round(
                self._add_noise(
                    self.patient.diastolic_bp,
                    SENSOR_CONFIG["diastolic_bp"]["noise"],
                )
            ),
        }