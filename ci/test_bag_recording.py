"""Tests for the optional ROS bag recorder launch description."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


LAUNCH_FILE = (
    Path(__file__).resolve().parents[1]
    / "genbu_reporting/launch/record_bag.launch.py"
)


class BagRecordingTests(unittest.TestCase):
    def test_records_all_topics_under_storage_bags(self):
        class LaunchDescription:
            def __init__(self, actions):
                self.actions = actions

        class ExecuteProcess:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        launch = types.ModuleType("launch")
        launch.LaunchDescription = LaunchDescription
        actions = types.ModuleType("launch.actions")
        actions.ExecuteProcess = ExecuteProcess

        with patch.dict(sys.modules, {"launch": launch, "launch.actions": actions}):
            spec = importlib.util.spec_from_file_location("record_bag", LAUNCH_FILE)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        process = module.generate_launch_description().actions[0]
        command = process.kwargs["cmd"]
        self.assertEqual(command[:4], ["ros2", "bag", "record", "-a"])
        self.assertEqual(command[4:8], [
            "--max-bag-size", "1000000000",
            "--max-bag-duration", "3600",
        ])
        self.assertEqual(command[8], "-o")
        self.assertRegex(command[9], r"^/mnt/storage/bags/genbu_\d{8}_\d{6}_\d{6}$")


if __name__ == "__main__":
    unittest.main()
