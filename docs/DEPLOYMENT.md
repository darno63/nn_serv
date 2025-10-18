# Deployment Guide

1. Provision infrastructure under `infrastructure/` (for Lambda Cloud, use `scripts/lambda_cloud_api.py` to launch or terminate instances; for other providers, plug in Terraform/Ansible as needed) to create the target VM(s) with sufficient RAM/GPU.
2. Run `scripts/bootstrap_server.sh` on the remote host to install Docker and NVIDIA tooling.
3. Build and push the container image:
   ```bash
   docker build -t your-registry/nn-serv:latest .
   docker push your-registry/nn-serv:latest
   ```
4. On the remote host, pull and run the container:
   ```bash
   docker run --gpus all -p 8000:8000 --env-file .env your-registry/nn-serv:latest
   ```
5. Monitor resource usage using `nvidia-smi`, `htop`, or integrate with Prometheus/Grafana.

## Lambda Cloud Quickstart

1. Export your API key: `export LAMBDA_API_KEY=...`.
2. Inspect capacity and pricing (optional):  
   `scripts/lambda_cloud_api.py list-instance-types --available-only`
3. (Optional) List existing persistent filesystems for model storage:  
   `scripts/lambda_cloud_api.py list-filesystems`  
   Create one via the console or Cloud API if you need a dedicated Wan2 volume.
   Prime the filesystem once (from a workstation or a mounted instance) so the weights persist:
   ```bash
   scripts/preload_model.py Wan-AI/Wan2.2-T2V-A14B /lambda/nfs/my-persistent-fs/Wan-AI
   ```
   Edit `configs/lambda/wan2-instance.yaml` to match your region, instance type, SSH key, and filesystem names.
4. Launch an instance and attach the filesystem so Wan2 stays warm between runs:  
   ```bash
   scripts/lambda_cloud_api.py launch-instance --config wan2-instance
   ```
   Pass flags like `--region` or `--ssh-key` to override the config for a one-off launch. The command prints the new instance ID and IP.
5. SSH to the instance using your private key (`ssh ubuntu@<INSTANCE_IP>`).
6. Execute `scripts/bootstrap_server.sh` on the instance if the base image lacks Docker or NVIDIA tooling.
7. (First run only) install the Wan2 runtime dependencies inside the container or host Python environment:
   ```bash
   pip install -r requirements/wan.txt
   # If you need the CUDA build of torch, reinstall with the appropriate index URL, e.g.
   # pip install --no-cache-dir --upgrade torch --index-url https://download.pytorch.org/whl/cu124
   ```
8. Pull and run the container image, bind-mounting the filesystem path that stores the Wan2 model (default `/lambda/nfs/<filesystem-name>`). Set `MODEL_DATA_DIR=/models` in `.env` so the app points to the mounted cache:
   ```bash
   docker run --gpus all \
     -p 8000:8000 \
     --env-file .env \
     -v /lambda/nfs/my-persistent-fs/Wan-AI:/models \
     your-registry/nn-serv:latest
   ```
9. When finished, tear down the instance to avoid charges:  
   `scripts/lambda_cloud_api.py terminate-instances <INSTANCE_ID>`
