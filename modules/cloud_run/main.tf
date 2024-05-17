resource "google_cloud_run_v2_service" "default" {
  name     = "ticket-review-app"
  location = "us-central1"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "gcr.io/${var.project}/ticket-review-app"
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      template[0].containers[0].name,
      client,
      client_version
    ]
  }
}
