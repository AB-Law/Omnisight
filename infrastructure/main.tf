provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Pub/Sub Topic (Free Tier)
resource "google_pubsub_topic" "raw_events" {
  name = "raw-events"
}

# 2. GCE Instance for PostgreSQL (Always Free e2-micro)
resource "google_compute_instance" "postgres_db" {
  name         = "omnisight-db"
  machine_type = "e2-micro" # Always Free Tier
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 10 # 10GB is within free tier (up to 30GB total)
    }
  }

  network_interface {
    network = "default"
    access_config {
      # Include this to give the instance a public IP
    }
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo docker run -d --name pg-db \
      -e POSTGRES_PASSWORD=${var.db_password} \
      -e POSTGRES_DB=omnisight_prod \
      -p 5432:5432 \
      postgres:15-alpine
  EOT

  tags = ["postgres"]
}

# 3. Firewalls for Postgres
resource "google_compute_firewall" "allow_postgres" {
  name    = "allow-postgres"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }

  source_ranges = ["0.0.0.0/0"] # WARNING: In prod, restrict to Cloud Run IPs
  target_tags   = ["postgres"]
}

# 4. Storage Bucket (Optional, for artifacts)
resource "google_storage_bucket" "artifacts" {
  name     = "${var.project_id}-omnisight-artifacts"
  location = var.region
  force_destroy = true
  uniform_bucket_level_access = true
}
