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
- For Lambda Cloud deployment, review `infrastructure/lambda/` and `docs/DEPLOYMENT.md`.
