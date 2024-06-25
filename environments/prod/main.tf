# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

data "google_project" "project" {}

provider "google" {
  project = var.project
}

resource "google_compute_global_address" "default" {
  name = "global-${var.app_name}-ip"
}

resource "google_service_account" "cloud-run-sa" {
  account_id   = "ticket-review-cloud-run-sa"
  display_name = "Ticket Review Cloud Run Service Account"
}

resource "google_project_iam_member" "cloud-run-sa-role-attachment" {
  for_each = toset([
    "roles/bigquery.user",
    "roles/bigquery.dataOwner",
    "roles/datastore.user"
  ])

  role       = each.key
  member = "serviceAccount:${google_service_account.cloud-run-sa.email}"
  project = var.project
}

resource "google_firestore_database" "database" {
  project     = var.project
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

resource "google_cloud_run_v2_service" "default" {
  name     = "${var.app_name}-app"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    containers {
      image = "gcr.io/${var.project}/${var.app_name}-app"
    }

    service_account = google_service_account.cloud-run-sa.email
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

resource "google_project_service_identity" "iap" {
  provider = google-beta

  project = var.project
  service = "iap.googleapis.com"
}


data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "serviceAccount:${google_project_service_identity.iap.email}",
    ]
  }
}

resource "google_cloud_run_v2_service_iam_policy" "noauth" {
  location = google_cloud_run_v2_service.default.location
  project  = google_cloud_run_v2_service.default.project
  name     = google_cloud_run_v2_service.default.name

  policy_data = data.google_iam_policy.noauth.policy_data
}

resource "google_compute_region_network_endpoint_group" "default" {
  provider              = google-beta
  project               = var.project
  name                  = "${var.app_name}-serverless-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.default.name
  }
}

resource "google_iap_client" "default" {
  display_name = "Test Client"
  brand        = "projects/${data.google_project.project.number}/brands/${var.brand_name}"
}

resource "google_compute_backend_service" "default" {
  provider = google-beta
  project  = var.project
  name     = "${var.app_name}-backend-service"

  backend {
    group = google_compute_region_network_endpoint_group.default.id
  }

  iap {
    oauth2_client_id = google_iap_client.default.client_id
    oauth2_client_secret = google_iap_client.default.secret
  }
}

resource "google_compute_url_map" "default" {
  provider        = google-beta
  project         = var.project
  name            = "${var.app_name}-url-map"
  default_service = google_compute_backend_service.default.id
}

resource "google_compute_managed_ssl_certificate" "default" {
  provider = google-beta
  project  = var.project
  name     = "${var.app_name}-ssl-cert"

  managed {
    domains = ["${var.app_name}.internal.doit.com"]
  }
}

resource "google_compute_target_https_proxy" "default" {
  provider = google-beta
  project  = var.project
  name     = "${var.app_name}-https-proxy"
  url_map  = google_compute_url_map.default.id
  ssl_certificates = [
    google_compute_managed_ssl_certificate.default.name
  ]
  depends_on = [
    google_compute_managed_ssl_certificate.default
  ]
}

resource "google_compute_global_forwarding_rule" "https" {
  provider              = google-beta
  project               = var.project
  name                  = "${var.app_name}-https"
  target                = google_compute_target_https_proxy.default.id
  ip_address            = google_compute_global_address.default.id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL"
}

resource "google_cloud_run_v2_service_iam_binding" "binding" {
  project  = var.project
  location = var.region
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  members = [
    "serviceAccount:${google_project_service_identity.iap.email}",
  ]
}

resource "google_bigquery_dataset" "sampled_data" {
  depends_on = [google_project_iam_member.cloud-run-sa-role-attachment]

  dataset_id    = "sampled_data"
  location      = "US"
}

resource "google_bigquery_data_transfer_config" "query_config" {
  depends_on = [google_project_iam_member.cloud-run-sa-role-attachment]

  display_name           = "update_ticket_review_source_table"
  location               = var.region
  data_source_id         = "scheduled_query"
  schedule               = "every 4 hours"
  destination_dataset_id = google_bigquery_dataset.sampled_data.dataset_id
  service_account_name   = google_service_account.cloud-run-sa.email
  params = {
    destination_table_name_template = "sampled_tickets"
    write_disposition               = "WRITE_TRUNCATE"
    query                           = "${file("${var.sql_file}")}"
  }
}