# Neural Network Service Infrastructure

Infrastructure-as-code friendly template for deploying RAM-intensive AI workloads to remote servers using containers.

## Repository Layout

```
├── configs/           # Configuration files (YAML/JSON) for models and services
├── infrastructure/    # Terraform/Ansible/etc. for provisioning and deployment
├── scripts/           # Automation scripts for CI/CD and maintenance
├── src/               # Application code (training, inference, utilities)
└── tests/             # Unit and integration tests
```

## Getting Started

1. Install Docker Engine (or Docker Desktop) and, if using NVIDIA GPUs, the NVIDIA Container Toolkit.
2. `python3 -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements/base.txt`
4. Build and run the container: `docker compose up --build`

## Next Steps

- Define your infrastructure provisioning strategy under `infrastructure/`.
- Add model configuration files inside `configs/`.
- Implement service entrypoints in `src/`.
- Add monitoring/exporter setup in `scripts/`.
- For Lambda Cloud deployment, use `scripts/lambda_cloud_api.py` and the guides in `infrastructure/lambda/` plus `docs/DEPLOYMENT.md`.
- Stage large models (e.g., Wan2) on a Lambda persistent filesystem (use `scripts/preload_model.py` to prime it), mount the volume in Docker (see `MODEL_DATA_DIR` in `.env.example`), and launch instances with `--filesystem` so weights persist across runs.

## Lambda Cloud Workflow (Wan2 Example)

1. **Prep credentials**  
   - Export `LAMBDA_API_KEY` and (if the model is gated) `HF_TOKEN`.  
   - Copy `.env.example` to `.env`, adjust `MODEL_CONFIG`, and keep `MODEL_DATA_DIR=/models`.

2. **Inspect capacity and filesystems**  
   ```bash
   scripts/lambda_cloud_api.py list-instance-types --available-only
   scripts/lambda_cloud_api.py list-filesystems
   ```
   Create a filesystem in the console or via API if you don’t already have one (e.g. `my-persistent-fs`).

3. **Prime the filesystem with Wan2 (run once)**  
   ```bash
   scripts/preload_model.py Wan-AI/Wan2.2-T2V-A14B /lambda/nfs/my-persistent-fs/Wan-AI
   ```
   This snapshot sticks around even after instances are terminated.

4. **Launch an inference node with the filesystem attached**  
   ```bash
   scripts/lambda_cloud_api.py launch-instance \
     --region us-south-1 \
     --instance-type gpu_1x_a100_sxm4 \
     --ssh-key my-key \
     --filesystem my-persistent-fs \
     --name nn-serv-worker
   ```
   The command prints the instance ID and public IP.

5. **Bootstrap and run the service**  
   ```bash
   ssh ubuntu@<INSTANCE_IP>
   ./scripts/bootstrap_server.sh              # installs Docker/NVIDIA toolkit if needed
   docker run --gpus all \
     -p 8000:8000 \
     --env-file .env \
     -v /lambda/nfs/my-persistent-fs/Wan-AI:/models \
     your-registry/nn-serv:latest
   ```
   Hugging Face caches and configs should reference `/models` (already reflected in `.env.example` and `configs/model.example.yaml`).

6. **Shut down when you’re done**  
   ```bash
   scripts/lambda_cloud_api.py terminate-instances <INSTANCE_ID>
   ```
   The filesystem (and Wan2 weights) stays intact for the next launch.
