import re

from simulation.sensor_data import SensorData
from simulation.gazebo_stream import stream_imu
from simulation.simulator import CareEdgeSimulator


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


def create_sensor_record(imu_data, physiological_data):

    return SensorData(
        patient_id=physiological_data["patient_id"],
        timestamp=imu_data["timestamp"],

        heart_rate=physiological_data["heart_rate"],
        spo2=physiological_data["spo2"],
        temperature=physiological_data["temperature"],

        systolic_bp=physiological_data["systolic_bp"],
        diastolic_bp=physiological_data["diastolic_bp"],

        accel_x=imu_data["accel_x"],
        accel_y=imu_data["accel_y"],
        accel_z=imu_data["accel_z"],

        gyro_x=imu_data["gyro_x"],
        gyro_y=imu_data["gyro_y"],
        gyro_z=imu_data["gyro_z"],

        activity=physiological_data["activity"],
        fall_detected=physiological_data["fall_detected"],
        event=physiological_data["event"],
    )


def main():

    print("CAREEDGE Sensor Pipeline")
    print("------------------------")
    print("Gazebo IMU + CAREEDGE physiological simulation")
    print("Press Ctrl+C to stop.\n")

    simulator = CareEdgeSimulator(patient_id="P001")

    # Start with a normal patient state.
    physiological_data = simulator.generate_reading("normal")

    try:

        for message in stream_imu():

            imu_data = parse_imu(message)

            if imu_data is None:
                continue

            record = create_sensor_record(
                imu_data,
                physiological_data,
            )

            print(record.to_json(), flush=True)

    except KeyboardInterrupt:

        print("\nPipeline stopped.")


if __name__ == "__main__":
    main()