from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true',
    )

    # Kill any stale slam_toolbox processes before starting to avoid conflicts
    # from previous launches that did not exit cleanly.
    kill_stale_slam = ExecuteProcess(
        cmd=[
            'bash', '-c',
            'pkill -SIGTERM async_slam_toolbox_node 2>/dev/null; '
            'timeout 5 bash -c \'while pgrep async_slam_toolbox_node > /dev/null; do sleep 0.5; done\'; '
            'exit 0',
        ],
        name='kill_stale_slam',
        output='screen',
    )

    # Launch slam_toolbox online async mapper
    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [FindPackageShare('slam_toolbox'), '/launch/online_async_launch.py']
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'slam_params_file': [
                FindPackageShare('genbu_navigation'),
                '/config/slam_toolbox_params.yaml',
            ],
        }.items(),
    )

    # Start slam_toolbox only after the stale-process cleanup finishes
    start_slam = RegisterEventHandler(
        OnProcessExit(
            target_action=kill_stale_slam,
            on_exit=[slam_toolbox],
        )
    )

    return LaunchDescription([
        use_sim_time_arg,
        kill_stale_slam,
        start_slam,
    ])
