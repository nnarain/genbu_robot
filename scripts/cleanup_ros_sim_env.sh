#!/usr/bin/env bash
set -euo pipefail

# Cleanup helper for stale ROS2/Gazebo/Nav2 simulation environments.
# Use before relaunch if you see duplicate node names, TF_OLD_DATA spam,
# mixed scan timestamps, or FastDDS SHM lock errors.

echo "[cleanup] stopping known sim/nav processes..."
patterns=(
  "ros2 launch genbu_simulator sim_navigation.launch.xml"
  "ros2 launch genbu_simulator sim_bringup.launch.xml"
  "gz sim"
  "parameter_bridge"
  "nav2_"
  "slam_toolbox"
  "rviz2"
  "joint_state_publisher"
)

for p in "${patterns[@]}"; do
  pkill -f "$p" >/dev/null 2>&1 || true
done

sleep 1

echo "[cleanup] force-killing any remaining gazebo/bridge processes..."
# shellcheck disable=SC2010
pids=$(ps -ef | grep -Ei 'gz sim|parameter_bridge|ros2 launch genbu_simulator' | grep -v grep | awk '{print $2}' || true)
if [[ -n "${pids}" ]]; then
  # shellcheck disable=SC2086
  kill -9 ${pids} >/dev/null 2>&1 || true
fi

echo "[cleanup] removing stale FastDDS shared-memory lock files..."
rm -f /dev/shm/fastrtps* /dev/shm/sem.fastrtps* || true

echo "[cleanup] restarting ros2 daemon..."
ros2 daemon stop >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true

echo "[cleanup] remaining relevant processes:"
ps -ef | grep -Ei 'gz sim|parameter_bridge|ros2 launch genbu_simulator|nav2_|slam_toolbox|rviz2' | grep -v grep || true

echo "[cleanup] done. Relaunch one stack only:"
echo "  ros2 launch genbu_simulator sim_navigation.launch.xml"
