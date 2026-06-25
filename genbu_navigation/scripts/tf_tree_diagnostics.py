#!/usr/bin/env python3

import rclpy
from diagnostic_msgs.msg import DiagnosticStatus
from diagnostic_updater import DiagnosticStatusWrapper, Updater
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener
from typing import Tuple


class TfTreeDiagnostics(Node):
    def __init__(self) -> None:
        super().__init__("tf_tree_diagnostics")
        self.declare_parameter("check_period_s", 1.0)
        self.declare_parameter("transform_timeout_s", 0.2)
        self.declare_parameter("transform_max_age_s", 2.0)
        self.declare_parameter(
            "required_transforms",
            ["map->odom", "odom->base_footprint", "base_footprint->laser"],
        )
        self.declare_parameter(
            "stale_check_transforms",
            ["map->odom", "odom->base_footprint"],
        )

        self._check_period = float(self.get_parameter("check_period_s").value)
        self._transform_timeout = float(self.get_parameter("transform_timeout_s").value)
        self._transform_max_age = float(self.get_parameter("transform_max_age_s").value)
        self._required_transforms = list(self.get_parameter("required_transforms").value)
        self._stale_check_transforms = set(
            self.get_parameter("stale_check_transforms").value
        )

        self._tf_buffer = Buffer(node=self)
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self._updater = Updater(self)
        self._updater.setHardwareID("tf_tree")
        self._updater.add("TF Tree", self._update_diagnostics)
        self._timer = self.create_timer(self._check_period, self._updater.force_update)

    def _parse_transform_spec(self, spec: str) -> Tuple[str, str]:
        parts = [part.strip() for part in spec.split("->", 1)]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Invalid transform specification '{spec}', expected parent_frame->child_frame"
            )
        return parts[0], parts[1]

    def _update_diagnostics(self, status: DiagnosticStatusWrapper) -> DiagnosticStatus:
        errors = []
        now = self.get_clock().now()
        timeout = Duration(seconds=self._transform_timeout)

        for spec in self._required_transforms:
            try:
                parent_frame, child_frame = self._parse_transform_spec(spec)
            except ValueError as exc:
                errors.append(str(exc))
                status.add(spec, "invalid specification")
                continue

            if not self._tf_buffer.can_transform(
                parent_frame, child_frame, Time(), timeout
            ):
                errors.append(f"missing transform {parent_frame}->{child_frame}")
                status.add(spec, "missing")
                continue

            try:
                transform = self._tf_buffer.lookup_transform(parent_frame, child_frame, Time())
            except TransformException as exc:
                errors.append(
                    f"lookup failed for {parent_frame}->{child_frame}: {str(exc)}"
                )
                status.add(spec, "lookup failed")
                continue

            stamp = Time.from_msg(transform.header.stamp)
            if stamp.nanoseconds == 0:
                status.add(spec, "ok (static)")
                continue

            age = (now - stamp).nanoseconds / 1e9
            if spec in self._stale_check_transforms and age > self._transform_max_age:
                errors.append(
                    f"stale transform {parent_frame}->{child_frame} ({age:.2f}s old)"
                )
                status.add(spec, f"stale ({age:.2f}s)")
                continue

            status.add(spec, f"ok ({age:.2f}s)")

        if errors:
            status.summary(DiagnosticStatus.ERROR, "; ".join(errors))
        else:
            status.summary(DiagnosticStatus.OK, "TF tree healthy")

        return status


def main() -> None:
    rclpy.init()
    node = TfTreeDiagnostics()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
