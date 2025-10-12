# Lambda Cloud Deployment

This directory contains Terraform templates and deployment notes for provisioning GPU instances on [Lambda Cloud](https://lambdalabs.com/service/gpu-cloud).

## Prerequisites

- Lambda Cloud account with API access enabled.
- `LAMBDA_API_KEY` environment variable exported with your API token.
- Terraform >= 1.6 installed locally.
- SSH key pair uploaded to Lambda Cloud (public key) for instance access.
- Docker/NVIDIA Container Toolkit installed on the image you intend to run.

## Workflow Overview

1. Use Terraform in `terraform/` to create or destroy Lambda instances.
2. Once the instance is up, run `scripts/bootstrap_server.sh` via SSH to install Docker/NVIDIA tooling (if not part of the image).
3. Build and push the container image from your workstation (or CI) to a registry accessible from the Lambda instance.
4. SSH into the instance and run the container with the desired model configuration.

## Notes

- Instances are billed while running. Destroy them with `terraform destroy` when idle.
- Ensure the selected instance type has sufficient system RAM and GPU VRAM for your model.
- Use Lambda's provided images (e.g., Ubuntu 22.04 with CUDA) to reduce setup time.
