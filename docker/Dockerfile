# syntax=docker/dockerfile:1
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

# Clone external dependencies (cached unless this layer changes)
RUN mkdir -p /ros_ws/src \
    && cd /ros_ws/src \
    && git clone https://github.com/nnarain/create_robot.git \
    && git clone https://github.com/nnarain/libcreate.git \
    && git clone https://github.com/nnarain/teleop_twist_joy.git --branch ds4-config

# Copy only package.xml files first so the rosdep layer is cached unless dependencies change
RUN mkdir -p /ros_ws/src/genbu_robot
COPY --parents */package.xml /ros_ws/src/genbu_robot/

RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi \
    && rosdep update \
    && apt-get update \
    && cd /ros_ws \
    && rosdep install --from-paths src --ignore-src -r -y \
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
