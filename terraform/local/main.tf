terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.38"
    }
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "kind-cloud-platform"
}

resource "kubernetes_namespace" "ecommerce" {
  metadata {
    name = var.namespace

    labels = {
      name = var.namespace
    }
  }
}

resource "kubernetes_config_map" "platform_metadata" {
  metadata {
    name      = "platform-metadata"
    namespace = kubernetes_namespace.ecommerce.metadata[0].name
  }

  data = {
    platform    = var.platform_name
    environment = var.environment
    managed_by  = "terraform"
  }
}
