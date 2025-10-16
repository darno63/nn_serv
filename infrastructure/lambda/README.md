# Lambda Cloud Deployment

Use these notes alongside `scripts/lambda_cloud_api.py` to create and manage GPU instances on [Lambda Cloud](https://lambda.ai/).

## Prerequisites

- Lambda Cloud account with API access enabled and a generated API key.
- `LAMBDA_API_KEY` exported in your shell (or passed via `--api-key`).
- SSH public key uploaded to Lambda Cloud for remote access.
- Docker + (optionally) NVIDIA Container Toolkit installed on the instance image you plan to use.

## Workflow Overview

1. Inspect capacity and pricing:
   ```bash
   scripts/lambda_cloud_api.py list-instance-types --available-only
   ```
2. (Optional) Create or list persistent filesystems for model assets:
   ```bash
   scripts/lambda_cloud_api.py list-filesystems
   # Create a filesystem via the console or Cloud API if you don't have one yet.
   ```
   Prime the filesystem once with the Wan2 weights (run from a workstation or a temporary instance):
   ```bash
   scripts/preload_model.py Wan-AI/Wan2.2-T2V-A14B /lambda/nfs/my-persistent-fs/Wan-AI
   ```
   Update `configs/lambda/wan2-instance.yaml` with your region, instance type, filesystem, and SSH key settings.
3. Upload or generate an SSH key if needed:
   ```bash
   scripts/lambda_cloud_api.py add-ssh-key --name my-key --public-key ~/.ssh/id_ed25519.pub
   ```
4. Launch an instance in your target region, attaching the filesystem so Wan2 stays resident between runs:
   ```bash
   scripts/lambda_cloud_api.py launch-instance --config wan2-instance
   ```
   Use flags such as `--region` or `--ssh-key` to override the config for a one-off run. The command prints the new instance ID; use it for SSH and lifecycle operations.
5. SSH into the instance using the printed public IP and run `scripts/bootstrap_server.sh` to install Docker/NVIDIA tooling if the base image lacks it.
6. Deploy your container, bind-mounting the filesystem path that holds the Wan2 weights (default mount path `/lambda/nfs/<filesystem-name>`):
   ```bash
   docker run --gpus all \
     -p 8000:8000 \
     --env-file .env \
     -v /lambda/nfs/my-persistent-fs/Wan-AI:/models \
     your-registry/nn-serv:latest
   ```
   Inside the container, point Hugging Face caches to `/models` (set `MODEL_DATA_DIR=/models` in `.env`) so the service reads the already-downloaded Wan2 assets.
7. When finished, terminate the instance to avoid charges:
   ```bash
   scripts/lambda_cloud_api.py terminate-instances <INSTANCE_ID>
   ```

## REST API Reference

The CLI script wraps the official Lambda Cloud REST API documented in the [Lambda Cloud API reference](https://docs.lambda.ai/api/cloud). If you need raw calls or automation in another language, consult the OpenAPI specification at `https://cloud.lambda.ai/api/v1/openapi.json`.
