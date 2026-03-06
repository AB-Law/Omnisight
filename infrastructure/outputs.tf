output "pubsub_topic" {
  value = google_pubsub_topic.raw_events.id
}

output "db_public_ip" {
  value = google_compute_instance.postgres_db.network_interface[0].access_config[0].nat_ip
}

output "storage_bucket" {
  value = google_storage_bucket.artifacts.url
}
