from datetime import datetime, timezone
from pathlib import Path

from launch import LaunchDescription
from launch.actions import ExecuteProcess


MAX_BAG_SIZE_BYTES = 1_000_000_000
MAX_BAG_DURATION_SECONDS = 3600


def generate_launch_description():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    output = Path("/mnt/storage/bags") / f"genbu_{timestamp}"

    return LaunchDescription([
        ExecuteProcess(
            cmd=[
                "ros2", "bag", "record", "-a",
                "--max-bag-size", str(MAX_BAG_SIZE_BYTES),
                "--max-bag-duration", str(MAX_BAG_DURATION_SECONDS),
                "-o", str(output),
            ],
            output="screen",
        ),
    ])
