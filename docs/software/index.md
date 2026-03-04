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

## Local Development

As this is a docker based system updates to the source primarily occurs using `docker pull`. However there is always the need for local software development. Synchronizing source code between machines can be a pain. So one solution here is to use `docker context` to build remotely on the raspberry pi while keeping the source workspace local.

```bash
docker context create robot --docker "host=ssh://<user>@<ip>"
```

From `genbu_robot` package.

```bash
docker build -t genbu:dev -f .\docker\Dockerfile .
```

On the Raspberry Pi:

```bash
nano /etc/default/genbu-robot
```

Update the docker image.

```ini
#GENBU_IMAGE=ghcr.io/nnarain/genbu_robot:latest
GENBU_IMAGE=genbu:dev
```