# Deployment Guide

1. Provision infrastructure (Terraform/Ansible) under `infrastructure/` to create the target VM(s) with sufficient RAM/GPU.
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
2. Copy `infrastructure/lambda/terraform/terraform.tfvars.example` to `terraform.tfvars` and fill in instance type, region, and SSH key name.
3. From `infrastructure/lambda/terraform`, run:
   ```bash
   terraform init
   terraform apply
   ```
4. After provisioning, SSH to the instance using the output IP and your private key.
5. Execute `scripts/bootstrap_server.sh` on the instance if the base image lacks Docker or NVIDIA tooling.
6. Pull and run the container image as described above.
7. When finished, run `terraform destroy` to avoid ongoing charges.
