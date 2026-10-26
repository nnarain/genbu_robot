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
ansible-playbook -i ansible/inventory.yml ansible/provision.yml --ask-pass
```

The playbook will:

- Download and install the latest `genbu-robot` Debian package from GitHub releases

The Debian package installs the [pixi](https://pixi.sh) binary to `/usr/local/bin`, the robot's pixi project (`pixi.toml` / `pixi.lock`) to `/etc/genbu-robot/`, and an intentionally empty `/etc/ros/setup.bash` customization hook. Add user-specific environment variables or source additional workspaces there; the `robot` systemd service sources it before running `pixi run -e robot`.

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

### Updating the pixi environment

The pixi environment is **not** updated automatically at runtime. It is defined by the `pixi.toml` / `pixi.lock` files shipped in the Debian package at `/etc/genbu-robot/`.

After updating the Debian package, restart the service to apply the new environment:

```bash
sudo systemctl restart robot
```

On restart, the service copies updated manifests from `/etc/genbu-robot/` into the robot-owned workspace at `/opt/genbu-robot/`. Legacy symlinks or hard links to the configuration files are replaced with independent copies so pixi cannot write back into `/etc`. Then `pixi run` syncs the environment in `/opt/genbu-robot/.pixi` to the copied `pixi.lock` before launching.

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

## Bag Recording

Bag recording is disabled by default. To record all ROS topics to `/mnt/storage/bags`, set `RECORD_BAG=true` in `/etc/default/genbu-robot` and restart the robot service:

```ini
RECORD_BAG=true
```

Each service start creates a uniquely named bag directory under `/mnt/storage/bags`. ROS 2 splits recording when a bag reaches 1 GB or one hour, whichever comes first.

### Starting the Web UI

The medkit gateway is started automatically by the `robot` systemd service (as part of `web.launch.xml`) and is accessible on port **8080**.

> **Note:** The `ros2_medkit_web_ui` web frontend was previously deployed as a Docker container on port 3000 and is not part of the pixi-based bringup. Run it separately if needed (see the [ros2_medkit_web_ui](https://github.com/selfpatch/ros2_medkit_web_ui) project).

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

The robot runs a pixi-managed environment, so software updates flow through new releases of the Debian package, which ships updated `pixi.toml` / `pixi.lock` files. For local development, use the pixi tasks defined in `pixi.toml` at the repository root:

- `pixi run build` — build the colcon workspace
- `pixi run sim` — build and launch the Gazebo simulation
- `pixi run robot` — build and launch the robot stack from source

To test changes on the robot itself, build a new Debian package (`dpkg-buildpackage -us -uc -b`), copy it to the Pi, and install it — or run a source workspace directly on the Pi using the `robot-src` pixi environment.

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