import subprocess


IMU_TOPIC = "/careedge/patient/imu"
GZ_WORKSPACE = r"C:\Users\Abhinav\gz-ws"


def stream_imu():

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
        cwd=GZ_WORKSPACE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    current_message = []

    try:

        for line in process.stdout:

            line = line.rstrip()

            if not line:
                continue

            # New Gazebo IMU message
            if line.startswith("header {"):

                # Return the previous complete message
                if current_message:
                    yield "\n".join(current_message)

                current_message = [line]

            elif current_message:

                current_message.append(line)

    except KeyboardInterrupt:

        process.terminate()


if __name__ == "__main__":

    print(f"Listening to {IMU_TOPIC}")

    for message in stream_imu():

        print("----- COMPLETE IMU MESSAGE -----")
        print(message)