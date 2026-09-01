import csv
import json
import re

from simulation.gazebo_stream import stream_imu
from simulation.simulator import CareEdgeSimulator


OUTPUT_FILE = "data/careedge_training_data.csv"


EVENT_SEQUENCE = [
    "normal",
    "normal",
    "tachycardia",
    "tachycardia",
    "hypoxia",
    "hypoxia",
    "fever",
    "fever",
    "hypertension",
    "hypertension",
    "fall",
]


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
        "patient_id": "P001",
        "timestamp": sec + nsec / 1_000_000_000,

        "accel_x": get_float(linear, "x"),
        "accel_y": get_float(linear, "y"),
        "accel_z": get_float(linear, "z"),

        "gyro_x": get_float(angular, "x"),
        "gyro_y": get_float(angular, "y"),
        "gyro_z": get_float(angular, "z"),
    }


def main():

    simulator = CareEdgeSimulator(patient_id="P001")

    records = []

    print("CAREEDGE training dataset generator")
    print("------------------------------------")

    for event in EVENT_SEQUENCE:

        print(f"Generating event: {event}")

        physiological = simulator.generate_reading(event)

        # Collect 50 IMU samples for this event.
        count = 0

        for message in stream_imu():

            imu = parse_imu(message)

            if imu is None:
                continue

            record = {
                "patient_id": physiological["patient_id"],
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
                "fall_detected": physiological["fall_detected"],

                "event": physiological["event"],
            }

            records.append(record)

            count += 1

            if count >= 50:
                break

    if not records:
        print("No records generated.")
        return

    fieldnames = list(records[0].keys())

    with open(OUTPUT_FILE, "w", newline="") as file:

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