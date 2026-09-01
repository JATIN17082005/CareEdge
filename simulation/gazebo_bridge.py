import json
import re
import subprocess


IMU_TOPIC = "/careedge/patient/imu"


def get_float(text, field):
    match = re.search(
        rf"{field}:\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        text,
    )

    if match:
        return float(match.group(1))

    return None


def main():

    command = [
        "pixi",
        "run",
        "gz",
        "topic",
        "-e",
        "-t",
        IMU_TOPIC,
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    print(f"Listening to Gazebo topic: {IMU_TOPIC}")
    print("Waiting for IMU data...")
    print("Press Ctrl+C to stop.")

    message = ""

    try:

        for line in process.stdout:

            line = line.rstrip()

            # Each message starts with header
            if line.startswith("header {"):

                # Process previous message if one exists
                if message:

                    process_message(message)

                message = ""

            message += line + "\n"

    except KeyboardInterrupt:

        process.terminate()
        print("\nBridge stopped.")


def process_message(message):

    # Extract timestamp
    sec = get_float(message, "sec")
    nsec = get_float(message, "nsec")

    timestamp = None

    if sec is not None and nsec is not None:
        timestamp = sec + nsec / 1_000_000_000

    # Extract linear acceleration block
    linear_match = re.search(
        r"linear_acceleration\s*\{(.*?)\}",
        message,
        re.DOTALL,
    )

    # Extract angular velocity block
    angular_match = re.search(
        r"angular_velocity\s*\{(.*?)\}",
        message,
        re.DOTALL,
    )

    if not linear_match or not angular_match:
        return

    linear = linear_match.group(1)
    angular = angular_match.group(1)

    data = {

        "patient_id": "P001",

        "timestamp": timestamp,

        "accel_x": get_float(linear, "x"),
        "accel_y": get_float(linear, "y"),
        "accel_z": get_float(linear, "z"),

        "gyro_x": get_float(angular, "x"),
        "gyro_y": get_float(angular, "y"),
        "gyro_z": get_float(angular, "z"),
    }

    print(json.dumps(data))


if __name__ == "__main__":
    main()