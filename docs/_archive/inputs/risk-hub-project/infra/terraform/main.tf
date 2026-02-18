# =============================================================================
# risk-hub Hetzner Infrastructure
# =============================================================================
#
# Terraform configuration für:
# - Cloud Network (privates Netz)
# - Load Balancer (TLS Termination)
# - App Server(s)
# - Worker Server
# - Database Server
# - Object Storage
#
# Usage:
#   cd infra/terraform/environments/prod
#   terraform init
#   terraform plan
#   terraform apply
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
  }

  # Remote State (empfohlen für Production)
  # backend "s3" {
  #   bucket   = "risk-hub-tfstate"
  #   key      = "prod/terraform.tfstate"
  #   region   = "eu-central-1"
  #   endpoint = "https://fsn1.your-objectstorage.com"
  # }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "hcloud" {
  token = var.hcloud_token
}

# =============================================================================
# Variables
# =============================================================================

variable "hcloud_token" {
  description = "Hetzner Cloud API Token"
  type        = string
  sensitive   = true
}

variable "environment" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Hetzner Datacenter Location"
  type        = string
  default     = "fsn1" # Falkenstein
}

variable "ssh_keys" {
  description = "SSH Key Names für Server-Zugriff"
  type        = list(string)
  default     = []
}

variable "domain" {
  description = "Base Domain für risk-hub"
  type        = string
  default     = "risk-hub.de"
}

# Server Sizing
variable "app_server_type" {
  description = "Server Type für App Server"
  type        = string
  default     = "cpx21" # 2 vCPU, 4 GB RAM
}

variable "app_server_count" {
  description = "Anzahl App Server"
  type        = number
  default     = 2
}

variable "worker_server_type" {
  description = "Server Type für Worker"
  type        = string
  default     = "cpx21"
}

variable "db_server_type" {
  description = "Server Type für Database"
  type        = string
  default     = "cpx31" # 4 vCPU, 8 GB RAM
}

# =============================================================================
# Network
# =============================================================================

resource "hcloud_network" "main" {
  name     = "risk-hub-${var.environment}"
  ip_range = "10.0.0.0/16"

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "hcloud_network_subnet" "app" {
  network_id   = hcloud_network.main.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = "10.0.1.0/24"
}

resource "hcloud_network_subnet" "db" {
  network_id   = hcloud_network.main.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = "10.0.2.0/24"
}

# =============================================================================
# Firewall
# =============================================================================

resource "hcloud_firewall" "app" {
  name = "risk-hub-app-${var.environment}"

  # SSH (nur von bestimmten IPs oder VPN)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"] # TODO: Einschränken!
  }

  # HTTP/HTTPS (für Let's Encrypt)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # App Port (intern für LB)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "8000"
    source_ips = ["10.0.0.0/16"]
  }

  # ICMP
  rule {
    direction  = "in"
    protocol   = "icmp"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  labels = {
    environment = var.environment
  }
}

resource "hcloud_firewall" "db" {
  name = "risk-hub-db-${var.environment}"

  # SSH
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["10.0.0.0/16"]
  }

  # PostgreSQL (nur aus App Subnet)
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "5432"
    source_ips = ["10.0.1.0/24"]
  }

  # Redis
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "6379"
    source_ips = ["10.0.1.0/24"]
  }

  labels = {
    environment = var.environment
  }
}

# =============================================================================
# SSH Keys
# =============================================================================

data "hcloud_ssh_keys" "all" {
  with_selector = "managed_by=terraform"
}

# =============================================================================
# App Servers
# =============================================================================

resource "hcloud_server" "app" {
  count       = var.app_server_count
  name        = "risk-hub-app-${var.environment}-${count.index + 1}"
  server_type = var.app_server_type
  location    = var.location
  image       = "ubuntu-24.04"

  ssh_keys = length(var.ssh_keys) > 0 ? var.ssh_keys : data.hcloud_ssh_keys.all.ssh_keys[*].name

  firewall_ids = [hcloud_firewall.app.id]

  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.1.${10 + count.index}"
  }

  labels = {
    environment = var.environment
    role        = "app"
    managed_by  = "terraform"
  }

  user_data = <<-EOF
    #cloud-config
    packages:
      - docker.io
      - docker-compose-v2
    runcmd:
      - systemctl enable docker
      - systemctl start docker
      - usermod -aG docker ubuntu
  EOF

  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# Worker Server
# =============================================================================

resource "hcloud_server" "worker" {
  name        = "risk-hub-worker-${var.environment}"
  server_type = var.worker_server_type
  location    = var.location
  image       = "ubuntu-24.04"

  ssh_keys = length(var.ssh_keys) > 0 ? var.ssh_keys : data.hcloud_ssh_keys.all.ssh_keys[*].name

  firewall_ids = [hcloud_firewall.app.id]

  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.1.50"
  }

  labels = {
    environment = var.environment
    role        = "worker"
    managed_by  = "terraform"
  }

  user_data = <<-EOF
    #cloud-config
    packages:
      - docker.io
      - docker-compose-v2
    runcmd:
      - systemctl enable docker
      - systemctl start docker
      - usermod -aG docker ubuntu
  EOF
}

# =============================================================================
# Database Server
# =============================================================================

resource "hcloud_server" "db" {
  name        = "risk-hub-db-${var.environment}"
  server_type = var.db_server_type
  location    = var.location
  image       = "ubuntu-24.04"

  ssh_keys = length(var.ssh_keys) > 0 ? var.ssh_keys : data.hcloud_ssh_keys.all.ssh_keys[*].name

  firewall_ids = [hcloud_firewall.db.id]

  network {
    network_id = hcloud_network.main.id
    ip         = "10.0.2.10"
  }

  labels = {
    environment = var.environment
    role        = "database"
    managed_by  = "terraform"
  }

  user_data = <<-EOF
    #cloud-config
    packages:
      - docker.io
      - docker-compose-v2
    runcmd:
      - systemctl enable docker
      - systemctl start docker
      - usermod -aG docker ubuntu
  EOF
}

# Database Volume (für persistente Daten)
resource "hcloud_volume" "db_data" {
  name      = "risk-hub-db-data-${var.environment}"
  size      = 50 # GB
  location  = var.location
  format    = "ext4"

  labels = {
    environment = var.environment
    role        = "database"
  }
}

resource "hcloud_volume_attachment" "db_data" {
  volume_id = hcloud_volume.db_data.id
  server_id = hcloud_server.db.id
  automount = true
}

# =============================================================================
# Load Balancer
# =============================================================================

resource "hcloud_load_balancer" "main" {
  name               = "risk-hub-lb-${var.environment}"
  load_balancer_type = "lb11"
  location           = var.location

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "hcloud_load_balancer_network" "main" {
  load_balancer_id = hcloud_load_balancer.main.id
  network_id       = hcloud_network.main.id
  ip               = "10.0.1.1"
}

# HTTP -> HTTPS Redirect
resource "hcloud_load_balancer_service" "http" {
  load_balancer_id = hcloud_load_balancer.main.id
  protocol         = "http"
  listen_port      = 80
  destination_port = 80

  http {
    redirect_http = true
  }
}

# HTTPS Service
resource "hcloud_load_balancer_service" "https" {
  load_balancer_id = hcloud_load_balancer.main.id
  protocol         = "https"
  listen_port      = 443
  destination_port = 8000

  http {
    certificates = [] # TODO: Add certificate IDs
    sticky_sessions = true
  }

  health_check {
    protocol = "http"
    port     = 8000
    interval = 10
    timeout  = 5
    retries  = 3
    http {
      path         = "/health/"
      status_codes = ["200"]
    }
  }
}

# LB Targets (App Servers)
resource "hcloud_load_balancer_target" "app" {
  count            = var.app_server_count
  load_balancer_id = hcloud_load_balancer.main.id
  type             = "server"
  server_id        = hcloud_server.app[count.index].id
  use_private_ip   = true
}

# =============================================================================
# Outputs
# =============================================================================

output "load_balancer_ip" {
  description = "Public IP des Load Balancers"
  value       = hcloud_load_balancer.main.ipv4
}

output "app_server_ips" {
  description = "Private IPs der App Server"
  value       = hcloud_server.app[*].network[*].ip
}

output "db_server_ip" {
  description = "Private IP des DB Servers"
  value       = hcloud_server.db.network[0].ip
}

output "worker_server_ip" {
  description = "Private IP des Worker Servers"
  value       = hcloud_server.worker.network[0].ip
}

output "network_id" {
  description = "Network ID für weitere Ressourcen"
  value       = hcloud_network.main.id
}
