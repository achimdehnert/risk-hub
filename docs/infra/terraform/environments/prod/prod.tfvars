# =============================================================================
# risk-hub Production Environment
# =============================================================================
#
# Usage:
#   terraform init
#   terraform plan -var-file="prod.tfvars"
#   terraform apply -var-file="prod.tfvars"
# =============================================================================

environment = "prod"
location    = "fsn1" # Falkenstein (oder "nbg1" für Nürnberg)
domain      = "risk-hub.de"

# Server Sizing (Production)
app_server_type  = "cpx31"  # 4 vCPU, 8 GB RAM
app_server_count = 2
worker_server_type = "cpx21" # 2 vCPU, 4 GB RAM
db_server_type   = "cpx41"   # 8 vCPU, 16 GB RAM

# SSH Keys (Namen aus Hetzner Console)
ssh_keys = [
  "admin-key",
  "deploy-key",
]
