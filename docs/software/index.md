# Software

Software documentation.

## Deployment

Install Raspberry Pi OS Lite on an SD card


ssh into the Raspberry Pi

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

