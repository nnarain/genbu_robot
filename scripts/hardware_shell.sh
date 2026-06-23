#!/usr/bin/env bash
# Open an interactive shell inside a privileged container with /dev mounted.
# Useful for inspecting or testing hardware access (serial ports, USB devices, etc.)
# without starting the full robot stack.
#
# Usage:
#   ./scripts/hardware_shell.sh [IMAGE]
#
# IMAGE defaults to the value of $GENBU_IMAGE, falling back to
#   ghcr.io/nnarain/genbu_robot:latest

set -euo pipefail

IMAGE="${1:-${GENBU_IMAGE:-ghcr.io/nnarain/genbu_robot:latest}}"

echo "[hardware-shell] launching privileged shell with /dev mounted"
echo "[hardware-shell] image: ${IMAGE}"

exec docker run --rm -it \
  --privileged \
  --network host \
  --volume /dev:/dev \
  "${IMAGE}" \
  /bin/bash -l
