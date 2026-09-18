output "namespace_name" {
  description = "Name of the Kubernetes namespace"
  value       = kubernetes_namespace.ecommerce.metadata[0].name
}

output "config_map_name" {
  description = "Name of the platform metadata ConfigMap"
  value       = kubernetes_config_map.platform_metadata.metadata[0].name
}
