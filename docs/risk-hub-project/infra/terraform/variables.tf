# =============================================================================
# risk-hub Terraform Variables
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

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Hetzner Datacenter Location"
  type        = string
  default     = "fsn1"

  validation {
    condition     = contains(["fsn1", "nbg1", "hel1", "ash"], var.location)
    error_message = "Location must be fsn1, nbg1, hel1, or ash."
  }
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

# =============================================================================
# Server Sizing
# =============================================================================

variable "app_server_type" {
  description = "Server Type für App Server"
  type        = string
  default     = "cpx21"
}

variable "app_server_count" {
  description = "Anzahl App Server"
  type        = number
  default     = 2

  validation {
    condition     = var.app_server_count >= 1 && var.app_server_count <= 10
    error_message = "App server count must be between 1 and 10."
  }
}

variable "worker_server_type" {
  description = "Server Type für Worker"
  type        = string
  default     = "cpx21"
}

variable "db_server_type" {
  description = "Server Type für Database"
  type        = string
  default     = "cpx31"
}

variable "db_volume_size" {
  description = "Database Volume Size in GB"
  type        = number
  default     = 50
}

# =============================================================================
# Optional: Monitoring Server
# =============================================================================

variable "enable_monitoring" {
  description = "Monitoring Server aktivieren"
  type        = bool
  default     = false
}

variable "monitoring_server_type" {
  description = "Server Type für Monitoring"
  type        = string
  default     = "cx22"
}
