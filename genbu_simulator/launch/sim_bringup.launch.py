from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import AnyLaunchDescriptionSource, PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='default',
        description='Name of the world file to load',
    )
    robot_name_arg = DeclareLaunchArgument(
        'robot_name',
        default_value='genbu',
        description='Name assigned to the spawned robot entity in Gazebo',
    )

    # Force Mesa software rendering for WSL / non-NVIDIA environments
    set_libgl = SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1')
    set_gallium = SetEnvironmentVariable('GALLIUM_DRIVER', 'llvmpipe')

    # Kill any stale Gazebo processes before starting to avoid conflicts from
    # previous launches that did not exit cleanly.
    kill_stale_gz = ExecuteProcess(
        cmd=[
            'bash', '-c',
            'pkill -SIGTERM gz_server 2>/dev/null; '
            'timeout 5 bash -c \'while pgrep gz_server > /dev/null; do sleep 0.5; done\'; '
            'exit 0',
        ],
        name='kill_stale_gz',
        output='screen',
    )

    # Launch Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare('ros_gz_sim'), '/launch/gz_sim.launch.py']
        ),
        launch_arguments={
            'gz_args': [
                '-r --headless-rendering ',
                FindPackageShare('genbu_simulator'),
                '/worlds/',
                LaunchConfiguration('world'),
                '.sdf',
            ]
        }.items(),
    )

    # Robot state publisher with sim time
    description = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            [FindPackageShare('genbu_description'), '/launch/description.launch']
        ),
        launch_arguments={'use_sim_time': 'true'}.items(),
    )

    # Spawn the robot entity in Gazebo
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_robot',
        output='screen',
        arguments=[
            '-topic', '/robot_description',
            '-name', LaunchConfiguration('robot_name'),
            '-allow_renaming', 'true',
        ],
    )

    # Gazebo <-> ROS 2 topic bridges
    gz_bridges = IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            [FindPackageShare('genbu_simulator'), '/launch/gz_bridges.launch.xml']
        )
    )

    # Start simulation components only after the stale-process cleanup finishes
    start_sim = RegisterEventHandler(
        OnProcessExit(
            target_action=kill_stale_gz,
            on_exit=[gz_sim, description, spawn_robot, gz_bridges],
        )
    )

    return LaunchDescription([
        world_arg,
        robot_name_arg,
        set_libgl,
        set_gallium,
        kill_stale_gz,
        start_sim,
    ])
