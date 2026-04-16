# syntax=docker/dockerfile:1-labs
ARG ROS_DISTRO=jazzy

FROM ros:${ROS_DISTRO}

ENV DEBIAN_FRONTEND=noninteractive

# Refresh apt signing keys from their canonical upstream sources.
# Avoids relying on the base image's potentially-stale keyring package.
# No hardcoded fingerprints: Ubuntu and ROS maintain these files at stable URLs.
RUN apt-get update -o Acquire::AllowInsecureRepositories=true -o Acquire::AllowDowngradeToInsecureRepositories=true || true \
    && apt-get install -y --allow-unauthenticated curl ca-certificates \
    && curl -fsSL https://archive.ubuntu.com/ubuntu/project/ubuntu-archive-keyring.gpg \
         -o /usr/share/keyrings/ubuntu-archive-keyring.gpg \
    && curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc \
         | gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg

# Bust the apt/rosdep cache weekly so fastcdr and nav2 binaries stay ABI-consistent.
# Set APT_CACHE_DATE to the current ISO week in CI (e.g. 2026-15) to force a weekly refresh.
ARG APT_CACHE_DATE
RUN echo "APT cache date: ${APT_CACHE_DATE}"

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
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

RUN cd /ros_ws \
    && . /opt/ros/${ROS_DISTRO}/setup.sh \
    && colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release


# Set up ROS environment
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc
RUN echo "source /ros_ws/install/setup.bash" >> ~/.bashrc

# Set working directory
WORKDIR /ros_ws

CMD ["/bin/bash", "-lc", "source /opt/ros/${ROS_DISTRO}/setup.bash && export COLCON_CURRENT_PREFIX=/ros_ws/install && source /ros_ws/install/setup.bash && ros2 launch genbu_bringup robot.launch.xml"]
