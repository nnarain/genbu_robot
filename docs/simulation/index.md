# Simulation

The `genbu_simulator` package provides a [Gazebo](https://gazebosim.org/) simulation environment for the Genbu robot.

## Prerequisites

- ROS 2 (Jazzy or later)
- `ros_gz_sim`, `ros_gz_bridge` packages
- `genbu_description` package

## Launching the Simulation

Use `sim_bringup.launch.xml` to start the full simulation stack:

```bash
ros2 launch genbu_simulator sim_bringup.launch.xml
```

This launch file:

1. Starts the Gazebo simulator with the selected world.
2. Launches the robot state publisher (with `use_sim_time:=true`).
3. Spawns the Genbu robot into the simulation.
4. Bridges the lidar sensor data from Gazebo to the ROS 2 `/scan` topic.

## Launch Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `world` | `default` | Name of the world file to load (see [Available Worlds](#available-worlds)). |
| `robot_name` | `genbu` | Name assigned to the spawned robot entity in Gazebo. |

### Selecting a World

Pass the `world` argument to choose a different simulation environment:

```bash
ros2 launch genbu_simulator sim_bringup.launch.xml world:=obstacle_course
```

## Available Worlds

| World | Description |
|-------|-------------|
| `default` | Empty flat plane with directional lighting. Good for basic bring-up testing. |
| `obstacle_course` | Flat plane populated with box pillars and cylinders placed around the robot's starting position to exercise obstacle detection and navigation. |

## ROS 2 Topics

Once the simulation is running, the following topics are available:

| Topic | Type | Description |
|-------|------|-------------|
| `/scan` | `sensor_msgs/msg/LaserScan` | Lidar scan data bridged from the Gazebo GPU lidar sensor. |
| `/robot_description` | `std_msgs/msg/String` | URDF published by the robot state publisher. |
| `/tf` | `tf2_msgs/msg/TFMessage` | Transform tree published by the robot state publisher. |

## Notes

### WSL / Non-NVIDIA Environments

The `sim_bringup.launch.xml` file automatically sets the following environment variables to enable Mesa software rendering when a hardware GPU is not available (e.g. WSL or CI environments):

| Variable | Value |
|----------|-------|
| `LIBGL_ALWAYS_SOFTWARE` | `1` |
| `GALLIUM_DRIVER` | `llvmpipe` |

No extra configuration is required; the launch file handles this automatically.
