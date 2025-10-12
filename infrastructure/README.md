# Infrastructure

Use this directory for infrastructure automation. Suggested layout:

- `terraform/` for provisioning compute (VMs, networks, storage).
- `ansible/` for configuring provisioned machines (drivers, containers, monitoring).
- `modules/` for shared Terraform modules.

Document required environment variables (cloud credentials) in each subfolder.
