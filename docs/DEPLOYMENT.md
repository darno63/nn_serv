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
4. Launch an instance and attach the filesystem so Wan2 stays warm between runs:  
   ```bash
   scripts/lambda_cloud_api.py launch-instance \
     --region us-south-1 \
     --instance-type gpu_1x_a100_sxm4 \
     --ssh-key my-key \
     --filesystem my-persistent-fs \
     --name nn-serv-worker
   ```
   The command prints the new instance ID and IP.
5. SSH to the instance using your private key (`ssh ubuntu@<INSTANCE_IP>`).
6. Execute `scripts/bootstrap_server.sh` on the instance if the base image lacks Docker or NVIDIA tooling.
7. Pull and run the container image, bind-mounting the filesystem path that stores the Wan2 model (default `/lambda/nfs/<filesystem-name>`). Set `MODEL_DATA_DIR=/models` in `.env` so the app points to the mounted cache:
   ```bash
   docker run --gpus all \
     -p 8000:8000 \
     --env-file .env \
     -v /lambda/nfs/my-persistent-fs/Wan-AI:/models \
     your-registry/nn-serv:latest
   ```
8. When finished, tear down the instance to avoid charges:  
   `scripts/lambda_cloud_api.py terminate-instances <INSTANCE_ID>`
