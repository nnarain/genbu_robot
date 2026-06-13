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

To update the `genbu-robot` Debian package to the latest release without re-running the full provisioning playbook:

```bash
ansible-playbook -i ansible/inventory.yml ansible/update.yml --ask-become-pass
```

This will remove the currently installed package and install the latest version from GitHub releases.

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

## Local Development

As this is a docker based system updates to the source primarily occurs using `docker pull`. However there is always the need for local software development. Synchronizing source code between machines can be a pain. So one solution here is to use `docker context` to build remotely on the raspberry pi while keeping the source workspace local.

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