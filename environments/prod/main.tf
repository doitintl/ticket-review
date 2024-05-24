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

resource "google_cloud_run_v2_service" "default" {
  name     = "${var.app_name}-app"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    containers {
      image = "gcr.io/${var.project}/${var.app_name}-app"
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

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
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

resource "google_project_service_identity" "iap" {
  provider = google-beta

  project = var.project
  service = "iap.googleapis.com"
}


resource "google_compute_backend_service" "default" {
  provider = google-beta
  project  = var.project
  name     = "${var.app_name}-backend-service"

  backend {
    group = google_compute_region_network_endpoint_group.default.id
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
