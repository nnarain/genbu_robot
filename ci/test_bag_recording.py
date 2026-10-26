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

        class Node:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        launch = types.ModuleType("launch")
        launch.LaunchDescription = LaunchDescription
        launch_ros = types.ModuleType("launch_ros")
        actions = types.ModuleType("launch_ros.actions")
        actions.Node = Node

        with patch.dict(sys.modules, {
            "launch": launch,
            "launch_ros": launch_ros,
            "launch_ros.actions": actions,
        }):
            spec = importlib.util.spec_from_file_location("record_bag", LAUNCH_FILE)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        node = module.generate_launch_description().actions[0].kwargs
        self.assertEqual(node["package"], "rosbag2_transport")
        self.assertEqual(node["executable"], "record")
        self.assertEqual(node["name"], "bag_recorder")
        self.assertEqual(node["arguments"][:1], ["-a"])
        self.assertEqual(node["arguments"][1:5], [
            "--max-bag-size", "1000000000",
            "--max-bag-duration", "3600",
        ])
        self.assertEqual(node["arguments"][5], "-o")
        self.assertRegex(
            node["arguments"][6], r"^/mnt/storage/bags/genbu_\d{8}_\d{6}_\d{6}$"
        )


if __name__ == "__main__":
    unittest.main()
