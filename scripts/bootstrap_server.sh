#!/usr/bin/env bash
set -euo pipefail

# Install base dependencies on a fresh server. Customize for your cloud provider.

if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

# Enable Docker for the current user
sudo usermod -aG docker "$USER"

# Install NVIDIA Container Toolkit if GPUs are present
if command -v nvidia-smi &>/dev/null; then
  distribution=$(. /etc/os-release; echo "$ID$VERSION_ID")
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit.gpg
  curl -fsSL "https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list" | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  sudo apt-get update
  sudo apt-get install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
fi
