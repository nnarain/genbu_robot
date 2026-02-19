ARG ROS_DISTRO=jazzy

FROM ros:${ROS_DISTRO}

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    git \
    python3-vcstool \
    python3-rosdep \
    build-essential \
    nano \
    && rm -rf /var/lib/apt/lists/*


# Build workspace from genbu_robot source root (Docker build context: this repo)
RUN mkdir -p /ros_ws/src/genbu_robot
COPY . /ros_ws/src/genbu_robot

RUN cd /ros_ws/src \
    && if [ ! -d create_robot ]; then git clone https://github.com/nnarain/create_robot.git; fi \
    && if [ ! -d libcreate ]; then git clone https://github.com/nnarain/libcreate.git; fi

RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi \
    && rosdep update \
    && apt-get update \
    && cd /ros_ws \
    && rosdep install --from-paths src --ignore-src -r -y

RUN cd /ros_ws \
    && . /opt/ros/${ROS_DISTRO}/setup.sh \
    && colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release


# Set up ROS environment
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
RUN echo "source /ros_ws/install/setup.bash" >> ~/.bashrc

# Set working directory
WORKDIR /ros_ws

CMD ["/bin/bash", "-lc", "source /opt/ros/${ROS_DISTRO}/setup.bash && source /ros_ws/install/setup.bash && ros2 launch genbu_bringup robot.launch.xml"]
