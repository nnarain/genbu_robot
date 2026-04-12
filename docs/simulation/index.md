# Simulation

The `genbu_simulator` package provides a [Gazebo](https://gazebosim.org/) simulation environment for the Genbu robot.

## Prerequisites

- ROS 2 (Jazzy or later)
- `ros_gz_sim`, `ros_gz_bridge` packages
- `genbu_description` package
- `nav2_bringup`, `slam_toolbox` packages (required for the navigation stack)

## Launching the Simulation

### Simulation Only

Use `sim_bringup.launch.xml` to start just the simulator without the navigation stack:

```bash
ros2 launch genbu_simulator sim_bringup.launch.xml
```

This launch file:

1. Starts the Gazebo simulator with the selected world.
2. Launches the robot state publisher (with `use_sim_time:=true`).
3. Spawns the Genbu robot into the simulation.
4. Bridges sensor and control topics between Gazebo and ROS 2.

### Simulation with Navigation Stack

Use `sim_navigation.launch.xml` to start the full stack — Gazebo, SLAM Toolbox, Nav2, and RViz — in a single command:

```bash
ros2 launch genbu_simulator sim_navigation.launch.xml
```

This launch file:

1. Starts the Gazebo simulator with the `maze` world (default).
2. Launches the robot state publisher and joint state publisher.
3. Spawns the Genbu robot into the simulation.
4. Bridges sensor and control topics between Gazebo and ROS 2.
5. Starts [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox) in online async mode for simultaneous localization and mapping.
6. Starts the [Nav2](https://nav2.org/) navigation stack (planner, controller, behavior trees, and lifecycle manager).
7. Opens RViz with the navigation configuration.

## Launch Arguments

### `sim_bringup.launch.xml`

| Argument | Default | Description |
|----------|---------|-------------|
| `world` | `default` | Name of the world file to load (see [Available Worlds](#available-worlds)). |
| `robot_name` | `genbu` | Name assigned to the spawned robot entity in Gazebo. |
| `use_lidar` | `true` | Include the RPLidar sensor in the robot description and enable simulation. |

### `sim_navigation.launch.xml`

| Argument | Default | Description |
|----------|---------|-------------|
| `world` | `maze` | Name of the world file to load. Defaults to the maze world for navigation testing. |
| `use_sim_time` | `true` | Use simulation clock for all nodes. |
| `use_lidar` | `true` | Include the RPLidar sensor in the robot description and enable simulation. |

### Selecting a World

Pass the `world` argument to choose a different simulation environment:

```bash
ros2 launch genbu_simulator sim_bringup.launch.xml world:=obstacle_course
```

```bash
ros2 launch genbu_simulator sim_navigation.launch.xml world:=obstacle_course
```

## Available Worlds

| World | Description |
|-------|-------------|
| `default` | Empty flat plane with directional lighting. Good for basic bring-up testing. |
| `maze` | 3×3 maze environment. Default world for navigation stack testing. |
| `obstacle_course` | Flat plane populated with box pillars and cylinders placed around the robot's starting position to exercise obstacle detection and navigation. |

## Navigation Stack Usage

Once `sim_navigation.launch.xml` is running, RViz opens automatically with the navigation configuration.

### Sending a Navigation Goal

1. In RViz, click the **Nav2 Goal** (or **2D Goal Pose**) button in the toolbar.
2. Click and drag in the map view to set the desired goal position and orientation.
3. The robot will plan a path and drive to the goal autonomously.

### TF Tree

The full TF tree when running with the navigation stack:

```
map            ← published by SLAM Toolbox
└── odom       ← bridged from Gazebo DiffDrive plugin
    └── base_footprint
        └── base_link
            ├── left_wheel_link
            ├── right_wheel_link
            ├── front_wheel_link
            ├── gyro_link
            └── rplidar_base_link
                └── rplidar_laser_link
```

### Navigation Stack Architecture

```
/goal_pose  (RViz Nav2 Goal tool)
    → bt_navigator → /plan → controller_server
                           → /cmd_vel_nav → velocity_smoother
                                          → /cmd_vel → Gazebo DiffDrive
```

## ROS 2 Topics

### Simulation Topics (always available)

| Topic | Type | Description |
|-------|------|-------------|
| `/scan` | `sensor_msgs/msg/LaserScan` | Lidar scan data bridged from the Gazebo GPU lidar sensor. |
| `/odom` | `nav_msgs/msg/Odometry` | Odometry bridged from the Gazebo DiffDrive plugin. |
| `/tf` | `tf2_msgs/msg/TFMessage` | Transform frames bridged from Gazebo (odom → base_footprint). |
| `/clock` | `rosgraph_msgs/msg/Clock` | Simulation clock bridged from Gazebo. |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Velocity commands forwarded to the Gazebo DiffDrive plugin. |
| `/robot_description` | `std_msgs/msg/String` | URDF published by the robot state publisher. |

### Navigation Topics (available with `sim_navigation.launch.xml`)

| Topic | Type | Description |
|-------|------|-------------|
| `/map` | `nav_msgs/msg/OccupancyGrid` | Occupancy grid map built by SLAM Toolbox. |
| `/goal_pose` | `geometry_msgs/msg/PoseStamped` | Navigation goal set via RViz or published directly. |
| `/plan` | `nav_msgs/msg/Path` | Planned path from the current position to the goal. |
| `/cmd_vel_nav` | `geometry_msgs/msg/Twist` | Velocity commands from the Nav2 controller before smoothing. |

## Notes

### WSL / Non-NVIDIA Environments

The `sim_bringup.launch.xml` file automatically sets the following environment variables to enable Mesa software rendering when a hardware GPU is not available (e.g. WSL or CI environments):

| Variable | Value |
|----------|-------|
| `LIBGL_ALWAYS_SOFTWARE` | `1` |
| `GALLIUM_DRIVER` | `llvmpipe` |

No extra configuration is required; the launch file handles this automatically.
