import math
import random


class FallMotionSimulator:
    """
    Procedurally generates a synthetic IMU signature for a fall episode.

    The pattern consists of:
    1. Pre-fall movement
    2. Brief reduced acceleration
    3. Impact spike
    4. Rotational spike
    5. Post-fall inactivity
    """

    def __init__(self, sample_rate=50):
        self.sample_rate = sample_rate

    def apply(self, imu, sample_index, total_samples):
        updated = imu.copy()

        # Progress through the current fall episode.
        progress = sample_index / max(total_samples - 1, 1)

        # -------------------------
        # Phase 1: pre-fall movement
        # -------------------------
        if progress < 0.30:
            updated["accel_x"] += random.uniform(-0.4, 0.4)
            updated["accel_y"] += random.uniform(-0.4, 0.4)

            updated["gyro_x"] += random.uniform(-0.8, 0.8)
            updated["gyro_y"] += random.uniform(-0.8, 0.8)

        # -------------------------
        # Phase 2: reduced support
        # -------------------------
        elif progress < 0.45:
            updated["accel_x"] += random.uniform(-0.2, 0.2)
            updated["accel_y"] += random.uniform(-0.2, 0.2)

            # Reduce the gravity component to simulate
            # a short free-fall-like interval.
            updated["accel_z"] *= random.uniform(0.05, 0.25)

            updated["gyro_x"] += random.uniform(-3.0, 3.0)
            updated["gyro_y"] += random.uniform(-3.0, 3.0)
            updated["gyro_z"] += random.uniform(-2.0, 2.0)

        # -------------------------
        # Phase 3: impact
        # -------------------------
        elif progress < 0.55:
            direction = random.choice([-1, 1])

            updated["accel_x"] += direction * random.uniform(2.0, 5.0)
            updated["accel_y"] += random.uniform(-3.0, 3.0)

            updated["accel_z"] += random.uniform(15.0, 25.0)

            updated["gyro_x"] += random.uniform(-8.0, 8.0)
            updated["gyro_y"] += random.uniform(-8.0, 8.0)
            updated["gyro_z"] += random.uniform(-6.0, 6.0)

        # -------------------------
        # Phase 4: post-impact settling
        # -------------------------
        elif progress < 0.70:
            decay = max(0.1, 1.0 - (progress - 0.55) / 0.15)

            updated["accel_x"] *= decay
            updated["accel_y"] *= decay
            updated["gyro_x"] *= decay
            updated["gyro_y"] *= decay
            updated["gyro_z"] *= decay

        # -------------------------
        # Phase 5: post-fall rest
        # -------------------------
        else:
            updated["accel_x"] += random.uniform(-0.05, 0.05)
            updated["accel_y"] += random.uniform(-0.05, 0.05)
            updated["accel_z"] = random.uniform(9.7, 9.9)

            updated["gyro_x"] = random.uniform(-0.02, 0.02)
            updated["gyro_y"] = random.uniform(-0.02, 0.02)
            updated["gyro_z"] = random.uniform(-0.02, 0.02)

        return updated