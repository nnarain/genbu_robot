# syntax=docker/dockerfile:1-labs
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
    usbutils \
    && rm -rf /var/lib/apt/lists/*

# Clone external dependencies (cached unless repos file changes)
COPY genbu_robot.repos /ros_ws/
RUN mkdir -p /ros_ws/src \
    && cd /ros_ws \
    && vcs import src < genbu_robot.repos

# Copy only package.xml files first so the rosdep layer is cached unless dependencies change
RUN mkdir -p /ros_ws/src/genbu_robot
COPY --parents */package.xml /ros_ws/src/genbu_robot/

RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi \
    && rosdep update \
    && apt-get update \
    && cd /ros_ws \
    && rosdep install --from-paths src --ignore-src -r -y \
    && apt-get install -y ros-${ROS_DISTRO}-librealsense2* \
    && apt-get install -y ros-${ROS_DISTRO}-realsense2-* \
    && rm -rf /var/lib/apt/lists/*

# Copy the full source and build (this layer re-runs on source changes)
COPY . /ros_ws/src/genbu_robot

RUN rm -rf /ros_ws/build /ros_ws/install /ros_ws/log \
    /ros_ws/src/genbu_robot/build /ros_ws/src/genbu_robot/install /ros_ws/src/genbu_robot/log

RUN cd /ros_ws \
    && . /opt/ros/${ROS_DISTRO}/setup.sh \
    && colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release


# Set up ROS environment
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
RUN echo "source /ros_ws/install/setup.bash" >> ~/.bashrc

# Set working directory
WORKDIR /ros_ws

CMD ["/bin/bash", "-lc", "source /opt/ros/${ROS_DISTRO}/setup.bash && export COLCON_CURRENT_PREFIX=/ros_ws/install && source /ros_ws/install/setup.bash && ros2 launch genbu_bringup robot.launch.xml"]
