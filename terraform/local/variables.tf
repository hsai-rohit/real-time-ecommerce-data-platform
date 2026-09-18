variable "namespace" {
  description = "Kubernetes namespace for the e-commerce platform"
  type        = string
  default     = "ecommerce"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "local"
}

variable "platform_name" {
  description = "Platform name stored in Kubernetes metadata"
  type        = string
  default     = "ecommerce-data-platform"
}
