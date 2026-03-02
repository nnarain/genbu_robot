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

### Manual installation

Install Raspberry Pi OS Lite on an SD card and ssh into the Pi:

```bash
ssh robot@<raspberry-ip>
```

Download and install the latest Debian package from GitHub releases.

1. Install tools

```bash
sudo apt update
sudo apt install -y curl
```

2. Download the consistently named `.deb` asset for your architecture

```bash
ARCH=$(dpkg --print-architecture)
curl -fL \
  "https://github.com/nnarain/genbu_robot/releases/download/debian-latest/genbu-robot-latest_${ARCH}.deb" \
  -o genbu-robot.deb
```

3. Install the package

```bash
sudo dpkg -i genbu-robot.deb
sudo apt -f install -y
```

You can also browse releases manually [here](https://github.com/nnarain/genbu_robot/releases/tag/debian-latest).

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