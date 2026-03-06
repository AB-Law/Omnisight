variable "project_id" {
  description = "The GCP Project ID"
  type        = str
}

variable "region" {
  description = "The GCP region"
  type        = str
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone for the GCE instance"
  type        = str
  default     = "us-central1-a"
}

variable "db_password" {
  description = "The password for the PostgreSQL database"
  type        = str
  sensitive   = true
}
