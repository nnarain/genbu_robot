#!/usr/bin/env python3
#
# HCDF file publisher
#
# @author Natesh Narain <nnaraindev@gmail.com>
#

from rclpy.node import Node
from std_msgs.msg import String
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSDurabilityPolicy

class HcdfPublisher(Node):
    def __init__(self, name: str):
        super().__init__(name)
    
        self._hcdf_file = self.declare_parameter('hcdf_file', '').get_parameter_value().string_value

        with open(self._hcdf_file, 'r') as f:
            self._hcdf_data = f.read()

        qos_profile = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
        )
        self._hcdf_pub = self.create_publisher(String, 'robot_topology', qos_profile)
        self._hcdf_msg = String()
        self._hcdf_msg.data = self._hcdf_data

        self._timer = self.create_timer(1.0, self.publish_hcdf)

    def publish_hcdf(self):
        self._hcdf_pub.publish(self._hcdf_msg)
        self._timer.cancel()  # Publish only once


if __name__ == '__main__':
    import rclpy

    rclpy.init()
    node = HcdfPublisher('hcdf_publisher')
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
