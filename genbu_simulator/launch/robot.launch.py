from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'gz_args',
            default_value='empty.sdf -r',
            description='Arguments to pass to Gazebo (world file and flags)',
        ),

        # Launch Gazebo (headless by default for Docker use)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('ros_gz_sim'),
                    'launch',
                    'gz_sim.launch.py',
                ])
            ]),
            launch_arguments={
                'gz_args': LaunchConfiguration('gz_args'),
            }.items(),
        ),

        # Publish robot description with simulation time enabled
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'use_sim_time': True,
                'robot_description': Command([
                    'xacro ',
                    PathJoinSubstitution([
                        FindPackageShare('genbu_description'),
                        'urdf',
                        'robot.urdf.xacro',
                    ]),
                ]),
            }],
        ),

        # Spawn the robot into Gazebo from the /robot_description topic
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', 'genbu',
                '-topic', 'robot_description',
            ],
            output='screen',
        ),
    ])
