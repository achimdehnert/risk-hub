# =============================================================================
# risk-hub Terraform Outputs
# =============================================================================
#
# Diese Outputs werden für Ansible Inventory und DNS Konfiguration benötigt.
# =============================================================================

output "load_balancer_ip" {
  description = "Public IPv4 des Load Balancers"
  value       = hcloud_load_balancer.main.ipv4
}

output "load_balancer_ipv6" {
  description = "Public IPv6 des Load Balancers"
  value       = hcloud_load_balancer.main.ipv6
}

output "app_server_ips" {
  description = "Private IPs der App Server"
  value = {
    for idx, server in hcloud_server.app : server.name => server.network[0].ip
  }
}

output "app_server_public_ips" {
  description = "Public IPs der App Server (für SSH)"
  value = {
    for idx, server in hcloud_server.app : server.name => server.ipv4_address
  }
}

output "worker_server_ip" {
  description = "Private IP des Worker Servers"
  value       = hcloud_server.worker.network[0].ip
}

output "worker_server_public_ip" {
  description = "Public IP des Worker Servers (für SSH)"
  value       = hcloud_server.worker.ipv4_address
}

output "db_server_ip" {
  description = "Private IP des Database Servers"
  value       = hcloud_server.db.network[0].ip
}

output "db_server_public_ip" {
  description = "Public IP des Database Servers (für SSH)"
  value       = hcloud_server.db.ipv4_address
}

output "network_id" {
  description = "Network ID für weitere Ressourcen"
  value       = hcloud_network.main.id
}

output "network_ip_range" {
  description = "IP Range des Netzwerks"
  value       = hcloud_network.main.ip_range
}

# =============================================================================
# Ansible Inventory Helper
# =============================================================================

output "ansible_inventory" {
  description = "Generiertes Ansible Inventory"
  sensitive   = false
  value       = <<-EOT
[all:vars]
ansible_user=root
ansible_python_interpreter=/usr/bin/python3
environment=${var.environment}
domain=${var.domain}

db_host=${hcloud_server.db.network[0].ip}
db_port=5432
db_name=risk_hub
db_user=app

redis_host=${hcloud_server.db.network[0].ip}
redis_port=6379

[app]
%{for idx, server in hcloud_server.app~}
${server.name} ansible_host=${server.ipv4_address} private_ip=${server.network[0].ip}
%{endfor~}

[worker]
${hcloud_server.worker.name} ansible_host=${hcloud_server.worker.ipv4_address} private_ip=${hcloud_server.worker.network[0].ip}

[database]
${hcloud_server.db.name} ansible_host=${hcloud_server.db.ipv4_address} private_ip=${hcloud_server.db.network[0].ip}

[docker:children]
app
worker
database

[risk_hub:children]
app
worker
database
EOT
}

# =============================================================================
# DNS Records (für Cloudflare/DNS Provider)
# =============================================================================

output "dns_records" {
  description = "DNS Records für manuelle Konfiguration"
  value = {
    # A Record für Hauptdomain
    "A" = {
      name  = "@"
      value = hcloud_load_balancer.main.ipv4
    }
    # Wildcard für Tenant-Subdomains
    "A_wildcard" = {
      name  = "*"
      value = hcloud_load_balancer.main.ipv4
    }
    # AAAA für IPv6
    "AAAA" = {
      name  = "@"
      value = hcloud_load_balancer.main.ipv6
    }
    "AAAA_wildcard" = {
      name  = "*"
      value = hcloud_load_balancer.main.ipv6
    }
  }
}
