# Genbu Robot — Agent Guidelines

## Working Model

The **user runs all long-lived processes** (Gazebo, RViz, Nav2, SLAM). The agent makes
code changes, interprets output the user pastes in, and asks the user to restart/rebuild
when needed.

**The agent must never:**
- Launch `ros2 launch` for the full sim stack in a terminal (Gazebo + RViz are GUI apps)
- Start background processes that outlive a single query
- Kill or restart the user's running simulation without explicit permission

**The agent may:**
- Run short one-shot read commands while the sim is running (e.g. `ros2 topic info`,
  `ros2 node list`, `ros2 topic echo --once`, `ros2 run tf2_tools view_frames`,
  `ros2 lifecycle list`)
- Run `colcon build` after making source changes
- Run `ros2 topic pub --once` for isolated one-shot tests

The agent should run one-shot diagnostics directly when needed, without asking the user
to copy/paste command output first.

With explicit user approval, the agent may run the cleanup script:
- `scripts/cleanup_ros_sim_env.sh`

---

## Typical Iteration Loop

```
Agent: makes source change → tells user what changed and why
User:  colcon build (if needed) → restarts simulation → reports output/errors
Agent: reads the output, diagnoses, proposes next change
```

When one-shot diagnostics are insufficient, the agent should then ask the user:

> "Please run `<command>` and paste the output here."

---

## Build

```bash
cd ~/workspace/ros_ws
colcon build --packages-select <package>
source install/setup.bash
```

Full stack build:
```bash
colcon build --packages-select genbu_description genbu_simulator genbu_navigation genbu_viz
source install/setup.bash
```

---

## Launch

Full simulation + SLAM + Nav2 + RViz:
```bash
ros2 launch genbu_simulator sim_navigation.launch.xml
```

Sim only (no Nav2):
```bash
ros2 launch genbu_simulator sim_bringup.launch.xml world:=maze
```

---

## Key Packages

| Package | Purpose |
|---|---|
| `genbu_description` | Robot URDF (Create 2 + RPLidar A1) |
| `genbu_simulator` | Gazebo worlds, bridges, launch files |
| `genbu_navigation` | Nav2 params + launch wrappers, SLAM config |
| `genbu_viz` | RViz configs |
| `genbu_bringup` | Real-robot bringup (not used in sim) |

---

## Key Files

| File | Purpose |
|---|---|
| `genbu_simulator/launch/sim_navigation.launch.xml` | Top-level launch: sim + SLAM + Nav2 + RViz |
| `genbu_simulator/launch/sim_bringup.launch.xml` | Sim + bridges only |
| `genbu_simulator/launch/gz_bridges.launch.xml` | Gazebo↔ROS bridges (single `parameter_bridge` node, YAML config) |
| `genbu_simulator/config/gz_bridges.yaml` | Bridge topic list (scan, odom, tf, clock, cmd_vel) |
| `genbu_simulator/worlds/maze.sdf` | Primary test world (3×3 maze) |
| `genbu_navigation/config/nav2_params.yaml` | Nav2 parameters for all servers |
| `genbu_navigation/config/slam_toolbox_params.yaml` | SLAM Toolbox config |
| `genbu_navigation/launch/nav2.launch.xml` | Wraps nav2_bringup/navigation_launch.py |
| `genbu_navigation/launch/localization.launch.xml` | Wraps slam_toolbox/online_async_launch.py |
| `genbu_viz/rviz/genbu_nav.rviz` | Navigation RViz config |

---

## Topic Wiring Reference

```
/goal_pose  (RViz SetGoal tool)
    → bt_navigator → /plan → controller_server
                           → /cmd_vel_nav → velocity_smoother
                                          → /cmd_vel → Gazebo DiffDrive
```

Gazebo bridges (`gz_bridges.yaml`):
- `/scan`     gz→ros  LaserScan
- `/odom`     gz→ros  Odometry
- `/tf`       gz→ros  TFMessage  (from Gazebo `/odom_tf` topic)
- `/clock`    gz→ros  Clock
- `/cmd_vel`  ros→gz  Twist

---

## TF Tree

```
map  (SLAM Toolbox)
└── odom  (Gazebo DiffDrive bridge)
    └── base_footprint  (fixed)
        └── base_link
            ├── left_wheel_link   (joint_state_publisher)
            ├── right_wheel_link  (joint_state_publisher)
            ├── front_wheel_link  (fixed joint)
            ├── gyro_link         (fixed joint)
            └── rplidar_base_link
                └── rplidar_laser_link
```

---

## Common Diagnostics

When something is wrong, the agent should run these directly first (if the sim is
already running):

```bash
# List lifecycle nodes, then check each state.
ros2 lifecycle nodes
for n in /planner_server /controller_server /bt_navigator /behavior_server /smoother_server /waypoint_follower; do ros2 lifecycle get $n; done

# Is the TF tree complete?
ros2 run tf2_tools view_frames

# Is /goal_pose wired to bt_navigator?
ros2 topic info /goal_pose --verbose

# Is velocity reaching Gazebo?
ros2 topic info /cmd_vel --verbose
ros2 topic echo /cmd_vel --once

# Is sim time flowing?
ros2 topic info /clock

# What's in the map?
ros2 topic echo /map --once | head -20

# Check for duplicate node names (should print nothing)
ros2 node list | sort | uniq -d
```

---

## Known Issues & Notes

- **Gazebo RTF**: worlds use `real_time_update_rate: 250` + `max_step_size: 0.004` to
  cap at 1× real-time. Without this, gz-sim runs uncapped and floods TF with
  out-of-order data causing `TF_OLD_DATA` warnings.
- **Clock bridge**: `/clock` must be bridged from Gazebo or all `use_sim_time=true`
  nodes stall. The clock bridge is in `gz_bridges.yaml`.
- **collision_monitor**: requires `observation_sources` in `nav2_params.yaml` or it
  blocks lifecycle activation for the entire Nav2 stack.
- **`cmd_vel` remapping**: Nav2 publishes to `cmd_vel_nav` → velocity_smoother →
  `cmd_vel`. The Gazebo bridge listens on `cmd_vel`. Both must exist.
- **Frame names**: sim uses `rplidar_laser_link` (not `laser`). Nav2 params use
  `base_footprint` (not `base_link`).
- **Stale sim processes**: `Ctrl+C` on launch can leave `gz sim server` alive. Multiple
  servers produce mixed `/clock`, `/scan`, and `/tf` timestamps, leading to message
  filter drops and `TF_OLD_DATA`/"earlier than transform cache" warnings.
- **FastDDS SHM lock errors**: `RTPS_TRANSPORT_SHM Error ... fastrtps_portXXXX` usually
  indicates stale `/dev/shm/fastrtps*` lock artifacts from crashed/stale processes.
- **Recovery workflow**: with user approval, run `scripts/cleanup_ros_sim_env.sh`, then
  relaunch exactly one sim stack.
