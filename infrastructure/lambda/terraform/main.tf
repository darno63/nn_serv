terraform {
  required_providers {
    lambda = {
      source  = "lambdalabs/lambda"
      version = "~> 0.3"
    }
  }
  required_version = ">= 1.6.0"
}

provider "lambda" {
  api_key = var.lambda_api_key
}

resource "lambda_instance" "inference" {
  # Adjust parameters based on desired capacity and pricing
  region_name       = var.region
  instance_type_name = var.instance_type
  ssh_key_name      = var.ssh_key_name

  # Optionally customize the OS image
  # See Lambda docs for available images (e.g., "ubuntu20.04-cuda-11.8")
  # image_name = "ubuntu22.04-cuda-12.1"

  tags = {
    project = var.project_name
    purpose = "nn-serv"
  }
}

output "instance_ip" {
  description = "Public IPv4 address of the Lambda instance"
  value       = lambda_instance.inference.ip
}
