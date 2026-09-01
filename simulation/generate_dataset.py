import csv
import random
import re

from simulation.fall_motion import FallMotionSimulator
from simulation.gazebo_stream import stream_imu
from simulation.simulator import CareEdgeSimulator
from simulation.patient_profiles import PATIENT_PROFILES


OUTPUT_FILE = "data/careedge_training_data.csv"

EVENTS = [
    "normal",
    "tachycardia",
    "hypoxia",
    "fever",
    "hypertension",
    "fall",
]

SAMPLES_PER_EVENT = 250


def get_float(text, field):
    match = re.search(
        rf"{field}:\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        text,
    )

    if match:
        return float(match.group(1))

    return None


def parse_imu(message):
    sec = get_float(message, "sec")
    nsec = get_float(message, "nsec")

    if sec is None or nsec is None:
        return None

    linear_match = re.search(
        r"linear_acceleration\s*\{(.*?)\}",
        message,
        re.DOTALL,
    )

    angular_match = re.search(
        r"angular_velocity\s*\{(.*?)\}",
        message,
        re.DOTALL,
    )

    if not linear_match or not angular_match:
        return None

    linear = linear_match.group(1)
    angular = angular_match.group(1)

    return {
        "timestamp": sec + nsec / 1_000_000_000,

        "accel_x": get_float(linear, "x"),
        "accel_y": get_float(linear, "y"),
        "accel_z": get_float(linear, "z"),

        "gyro_x": get_float(angular, "x"),
        "gyro_y": get_float(angular, "y"),
        "gyro_z": get_float(angular, "z"),
    }


def create_simulator(patient_id):
    profile = PATIENT_PROFILES[patient_id]

    return CareEdgeSimulator(
        patient_id=patient_id,
        **profile,
    )


def main():

    records = []

    patient_ids = list(PATIENT_PROFILES.keys())

    print("CAREEDGE training dataset generator")
    print("------------------------------------")
    print(f"Patients: {len(patient_ids)}")
    print(f"Events: {len(EVENTS)}")
    print(f"Samples per event: {SAMPLES_PER_EVENT}")
    print()

    fall_simulator = FallMotionSimulator(sample_rate=50)

    print("Connecting to Gazebo IMU stream...")

    imu_stream = stream_imu()

    for patient_id in patient_ids:

        print()
        print(f"Patient: {patient_id}")

        simulator = create_simulator(patient_id)

        for event in EVENTS:

            print(f"Generating event: {event}")

            for sample_index in range(SAMPLES_PER_EVENT):

                imu = None

                while imu is None:
                    try:
                        message = next(imu_stream)
                    except StopIteration:
                        print("Gazebo IMU stream ended.")
                        return

                    imu = parse_imu(message)

                physiological = simulator.generate_reading(event)

                if event == "fall":
                    imu = fall_simulator.apply(
                        imu,
                        sample_index=sample_index,
                        total_samples=SAMPLES_PER_EVENT,
                    )

                record = {
                    "patient_id": patient_id,
                    "timestamp": imu["timestamp"],

                    "heart_rate": physiological["heart_rate"],
                    "spo2": physiological["spo2"],
                    "temperature": physiological["temperature"],

                    "systolic_bp": physiological["systolic_bp"],
                    "diastolic_bp": physiological["diastolic_bp"],

                    "accel_x": imu["accel_x"],
                    "accel_y": imu["accel_y"],
                    "accel_z": imu["accel_z"],

                    "gyro_x": imu["gyro_x"],
                    "gyro_y": imu["gyro_y"],
                    "gyro_z": imu["gyro_z"],

                    "activity": physiological["activity"],

                    "fall_detected": event == "fall",

                    "event": event,
                }

                records.append(record)

    random.shuffle(records)

    if not records:
        print("No records generated.")
        return

    fieldnames = list(records[0].keys())

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(records)

    print()
    print(f"Generated {len(records)} records.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()