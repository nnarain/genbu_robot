from datetime import datetime, timezone
from pathlib import Path

from launch import LaunchDescription
from launch.actions import ExecuteProcess


def generate_launch_description():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    output = Path("/mnt/storage/bags") / f"genbu_{timestamp}"

    return LaunchDescription([
        ExecuteProcess(
            cmd=["ros2", "bag", "record", "-a", "-o", str(output)],
            output="screen",
        ),
    ])
