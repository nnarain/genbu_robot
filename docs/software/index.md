# Software

Software documentation.

## Deployment

### Ansible (recommended)

The `ansible/` directory in this repository contains a playbook that provisions a clean Raspberry Pi OS image with everything needed to run the Genbu robot software stack.

**Prerequisites (on your local machine)**

```bash
pip install ansible
```

**Steps**

1. Flash [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/) onto an SD card and boot the Pi.

2. Edit `ansible/inventory.yml` and set the correct IP address for your Raspberry Pi:

```yaml
all:
  hosts:
    genbu:
      ansible_host: 192.168.1.100  # replace with your Raspberry Pi's IP address
      ansible_user: robot
```

3. Run the provisioning playbook from the repository root:

```bash
ansible-playbook -i ansible/inventory.yml ansible/provision.yml --ask-become-pass
```

The playbook will:

- Install Docker Engine
- Download and install the latest `genbu-robot` Debian package from GitHub releases

### Updating the Debian Package

#### On the robot (self-update)

The `genbu-robot-update` script is installed on the robot as part of the Debian package and provides a simple way to pull and install the latest release directly from GitHub:

```bash
sudo genbu-robot-update
```

This will download the latest `genbu-robot` Debian package for the current architecture from GitHub releases and install it.

#### From a remote machine (Ansible)

To update the `genbu-robot` Debian package to the latest release without re-running the full provisioning playbook:

```bash
ansible-playbook -i ansible/inventory.yml ansible/update.yml --ask-become-pass
```

This will remove the currently installed package and install the latest version from GitHub releases.

### Updating the Docker Image

The Docker image is **not** pulled automatically on startup. To pull the latest image manually, use the `genbu-robot-docker-update` script:

```bash
sudo genbu-robot-docker-update
```

This script will:

1. Prune unused Docker images to free disk space before pulling.
2. Pull the latest image defined in `/etc/genbu-robot/docker-compose.yml`.
3. Prune any dangling images left over after the pull.

After updating the image, restart the service to use it:

```bash
sudo systemctl restart robot
```

## Foxglove

[Foxglove](https://foxglove.dev/) provides a web-based visualization and debugging interface for ROS systems.

### Enabling / Disabling

Foxglove is enabled by default. To disable it, set `ENABLE_FOXGLOVE=false` in `/etc/default/genbu-robot`:

```ini
ENABLE_FOXGLOVE=false
```

### Starting the Foxglove Bridge

The `genbu_web` package contains a launch file that starts the Foxglove bridge:

```bash
ros2 launch genbu_web web.launch.xml
```

This starts the bridge on port `8765`.

### Accessing Foxglove

1. Open [https://app.foxglove.dev](https://app.foxglove.dev) in your browser (or use the desktop app).
2. Click **Open connection**.
3. Select **Rosbridge / Foxglove WebSocket** and enter the WebSocket URL:

```
ws://<robot-ip>:8765
```

Replace `<robot-ip>` with the IP address of your robot.

## Medkit SOVD Web UI

[ros2_medkit](https://github.com/selfpatch/ros2_medkit) exposes a diagnostic REST API following the SOVD (Service-Oriented Vehicle Diagnostics) standard. The **medkit web UI** is a lightweight browser-based interface for browsing the SOVD entity tree.

### Enabling / Disabling

Medkit is enabled by default. To disable it, set `ENABLE_MEDKIT=false` in `/etc/default/genbu-robot`:

```ini
ENABLE_MEDKIT=false
```

### Starting the Web UI

The web UI is started automatically as part of the Docker Compose stack:

```bash
docker compose -f /etc/genbu-robot/docker-compose.yml up
```

It runs as the `ros2_medkit_web_ui` container and is accessible on host port **3000** (mapped from container port 80).

### Accessing the Web UI

1. Open `http://<robot-ip>:3000` in your browser.
2. In the connection dialog, enter the medkit gateway URL:

```
http://<robot-ip>:8080
```

3. Click **Connect** to browse the entity tree.

Replace `<robot-ip>` with the IP address of your robot.

## Netplan Auto-Recovery

The Genbu provisioning playbook installs a one-shot systemd service (`genbu-netplan-recovery`) that runs on every boot to guard against corrupted or empty Netplan configuration files.

### What it does

On each boot the service:

1. Checks whether `/etc/netplan/` is healthy:
   - If any `90-nm-*.yaml` file exists, none of them may be empty (if no such files exist at all, this check is skipped — absence is valid when `wlan0` is configured via a hand-crafted YAML).
   - At least one YAML file references `wlan0`.
2. **Healthy** → backs up `/etc/netplan/` to `/var/lib/genbu/netplan-config.tar.gz`.
3. **Corrupted** → moves the broken config to `/etc/netplan.corrupted.<timestamp>`, restores from the backup, and restarts NetworkManager.

All actions are logged to `/var/log/genbu-netplan-recovery.log` and the systemd journal:

```bash
journalctl -u genbu-netplan-recovery
```

### Manual Recovery

If the service cannot auto-recover (e.g. no backup exists yet), connect via serial console and run:

```bash
# Inspect backup contents
tar -tzf /var/lib/genbu/netplan-config.tar.gz

# Restore manually
sudo tar -xzf /var/lib/genbu/netplan-config.tar.gz -C /etc

# Restart networking
sudo systemctl restart NetworkManager

# Verify
nmcli device status
```

The corrupted files are preserved under `/etc/netplan.corrupted.<timestamp>` for post-mortem inspection.

## Local Development

As this is a docker based system updates to the source primarily occurs using `docker pull`. However there is always the need for local software development. Synchronizing source code between machines can be a pain. So one solution here is to use `docker context` to build remotely on the raspberry pi while keeping the source workspace local.

### YDLidar SDK prerequisite

The ROS 2 package `ydlidar_ros2_driver` depends on the native [`YDLidar-SDK`](https://github.com/YDLIDAR/YDLidar-SDK), which must be built and installed before running `colcon build` in a fresh workspace.

If your workspace was created from `genbu_robot.repos`, the SDK is imported under `/ros_ws/src/YDLIDAR/YDLidar-SDK`. Build and install it with:

```bash
mkdir -p /tmp/ydlidar-sdk-build
cd /tmp/ydlidar-sdk-build
cmake /ros_ws/src/YDLIDAR/YDLidar-SDK -DCMAKE_INSTALL_PREFIX=/usr/local
make -j"$(nproc)"
sudo make install
```

**Note:** The build is performed outside `/ros_ws` to isolate the SDK from source tree changes. CMake will discover the installed SDK via `ydlidar_sdkConfig.cmake` in `/usr/local/lib/cmake` during `colcon build`.

```bash
docker context create robot --docker "host=ssh://<user>@<ip>"
```

From `genbu_robot` package.

```bash
docker build -t genbu:dev -f .\docker\Dockerfile .
```

On the Raspberry Pi, update `/etc/default/genbu-robot` to point to the custom image:

```bash
nano /etc/default/genbu-robot
```

```ini
GENBU_IMAGE=genbu:dev
```

To bring the stack up or down manually using Docker Compose:

```bash
# Bring up
GENBU_IMAGE=genbu:dev docker compose -f /etc/genbu-robot/docker-compose.yml up

# Tear down
docker compose -f /etc/genbu-robot/docker-compose.yml down
```