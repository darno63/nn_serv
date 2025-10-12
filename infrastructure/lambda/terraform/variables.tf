variable "lambda_api_key" {
  description = "Lambda Cloud API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Lambda Cloud region to deploy in"
  type        = string
  default     = "us-south-1"
}

variable "instance_type" {
  description = "Lambda Cloud instance type slug (e.g., gpu_1x_a100_sxm4)"
  type        = string
}

variable "ssh_key_name" {
  description = "Name of the SSH key uploaded to Lambda Cloud"
  type        = string
}

variable "project_name" {
  description = "Tag to identify project resources"
  type        = string
  default     = "nn-serv"
}
