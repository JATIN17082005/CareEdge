import time
from datetime import datetime
from simulation.patient import Patient
from simulation.sensors import SensorSimulator
from simulation.scenarios import ScenarioManager


class CareEdgeSimulator:
    def __init__(
        self,
        patient_id="P001",
        heart_rate=75,
        spo2=98,
        temperature=36.8,
        systolic_bp=120,
        diastolic_bp=80,
    ):
        self.patient = Patient(
            patient_id=patient_id,
            heart_rate=heart_rate,
            spo2=spo2,
            temperature=temperature,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
        )

        self.sensors = SensorSimulator(self.patient)
        self.scenarios = ScenarioManager()

    def generate_reading(self, event="normal"):
        self.scenarios.set_event(event)
        sensor_reading = self.sensors.read()
        final_reading = self.scenarios.apply_current_event(sensor_reading)

        final_reading["timestamp"] = datetime.now().isoformat(timespec="seconds")

        return final_reading

    def run(self, event_sequence, interval=1):
        for event in event_sequence:
            reading = self.generate_reading(event)

            print("-" * 50)
            print(f"Event: {event}")
            print(f"Patient: {reading['patient_id']}")
            print(f"Heart Rate: {reading['heart_rate']} BPM")
            print(f"SpO2: {reading['spo2']} %")
            print(f"Temperature: {reading['temperature']} °C")
            print(
                f"Blood Pressure: "
                f"{reading['systolic_bp']}/{reading['diastolic_bp']} mmHg"
            )
            print(f"Activity: {reading['activity']}")
            print(f"Fall Detected: {reading['fall_detected']}")

            time.sleep(interval)