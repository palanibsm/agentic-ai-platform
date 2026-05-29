# ── IAP (Identity-Aware Proxy) ────────────────────────────────────────────────
# Secures portal and ide-chat behind Google login.
#
# Architecture:
#   Browser → Global LB (HTTPS, managed cert) → IAP check → Serverless NEG
#            → Cloud Run (ingress: INTERNAL_LOAD_BALANCER only)
#
# After apply:
#   1. Point portal_domain DNS A record → portal_lb_ip (terraform output)
#   2. Point ide_chat_domain DNS A record → ide_chat_lb_ip (terraform output)
#   3. Wait ~15 min for managed SSL certs to provision
#   4. Users visit https://<domain> → Google login → app

# ── OAuth clients (created manually — personal projects can't use the API) ────
# 1. GCP Console → APIs & Services → OAuth consent screen → External → Create
# 2. GCP Console → Credentials → Create Credentials → OAuth client ID
#    (Web application) — create one for portal, one for ide-chat
# 3. Paste the client IDs and secrets into terraform.tfvars:
#      iap_portal_client_id     = "..."
#      iap_portal_client_secret = "..."
#      iap_ide_chat_client_id   = "..."
#      iap_ide_chat_client_secret = "..."

# ── Global static IPs ─────────────────────────────────────────────────────────
resource "google_compute_global_address" "portal_ip" {
  name    = "portal-ip"
  project = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_compute_global_address" "ide_chat_ip" {
  name    = "ide-chat-ip"
  project = var.project_id

  depends_on = [google_project_service.apis]
}

# ── Serverless NEGs ───────────────────────────────────────────────────────────
# Bridge between the global LB and Cloud Run services.
resource "google_compute_region_network_endpoint_group" "portal_neg" {
  name                  = "portal-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.project_id

  cloud_run {
    service = google_cloud_run_v2_service.portal.name
  }

  depends_on = [google_project_service.apis]
}

resource "google_compute_region_network_endpoint_group" "ide_chat_neg" {
  name                  = "ide-chat-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.project_id

  cloud_run {
    service = google_cloud_run_v2_service.ide_chat.name
  }

  depends_on = [google_project_service.apis]
}

# ── Backend services with IAP enabled ─────────────────────────────────────────
resource "google_compute_backend_service" "portal_backend" {
  name                  = "portal-backend"
  project               = var.project_id
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.portal_neg.id
  }

  iap {
    oauth2_client_id     = var.iap_portal_client_id
    oauth2_client_secret = var.iap_portal_client_secret
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_backend_service" "ide_chat_backend" {
  name                  = "ide-chat-backend"
  project               = var.project_id
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.ide_chat_neg.id
  }

  iap {
    oauth2_client_id     = var.iap_ide_chat_client_id
    oauth2_client_secret = var.iap_ide_chat_client_secret
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# ── URL maps ──────────────────────────────────────────────────────────────────
resource "google_compute_url_map" "portal_urlmap" {
  name            = "portal-urlmap"
  project         = var.project_id
  default_service = google_compute_backend_service.portal_backend.id
}

resource "google_compute_url_map" "ide_chat_urlmap" {
  name            = "ide-chat-urlmap"
  project         = var.project_id
  default_service = google_compute_backend_service.ide_chat_backend.id
}

# ── Google-managed SSL certificates ───────────────────────────────────────────
# Provision automatically once DNS A records point to the LB IPs.
resource "google_compute_managed_ssl_certificate" "portal_cert" {
  # Name includes a hash of the domain so Terraform can create-before-destroy
  # safely when the domain changes.
  name    = "portal-cert-${substr(sha256(var.portal_domain), 0, 8)}"
  project = var.project_id

  managed {
    domains = [var.portal_domain]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_managed_ssl_certificate" "ide_chat_cert" {
  name    = "ide-chat-cert-${substr(sha256(var.ide_chat_domain), 0, 8)}"
  project = var.project_id

  managed {
    domains = [var.ide_chat_domain]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ── HTTPS target proxies ───────────────────────────────────────────────────────
resource "google_compute_target_https_proxy" "portal_proxy" {
  name             = "portal-https-proxy"
  project          = var.project_id
  url_map          = google_compute_url_map.portal_urlmap.id
  ssl_certificates = [google_compute_managed_ssl_certificate.portal_cert.id]
}

resource "google_compute_target_https_proxy" "ide_chat_proxy" {
  name             = "ide-chat-https-proxy"
  project          = var.project_id
  url_map          = google_compute_url_map.ide_chat_urlmap.id
  ssl_certificates = [google_compute_managed_ssl_certificate.ide_chat_cert.id]
}

# ── HTTP → HTTPS redirect ─────────────────────────────────────────────────────
resource "google_compute_url_map" "https_redirect" {
  name    = "https-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "https_redirect" {
  name    = "https-redirect-proxy"
  project = var.project_id
  url_map = google_compute_url_map.https_redirect.id
}

# ── Global forwarding rules (HTTPS) ───────────────────────────────────────────
resource "google_compute_global_forwarding_rule" "portal_https" {
  name                  = "portal-https"
  project               = var.project_id
  target                = google_compute_target_https_proxy.portal_proxy.id
  port_range            = "443"
  ip_address            = google_compute_global_address.portal_ip.address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_compute_global_forwarding_rule" "ide_chat_https" {
  name                  = "ide-chat-https"
  project               = var.project_id
  target                = google_compute_target_https_proxy.ide_chat_proxy.id
  port_range            = "443"
  ip_address            = google_compute_global_address.ide_chat_ip.address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# ── Global forwarding rules (HTTP → HTTPS redirect) ───────────────────────────
resource "google_compute_global_forwarding_rule" "portal_http_redirect" {
  name                  = "portal-http-redirect"
  project               = var.project_id
  target                = google_compute_target_http_proxy.https_redirect.id
  port_range            = "80"
  ip_address            = google_compute_global_address.portal_ip.address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_compute_global_forwarding_rule" "ide_chat_http_redirect" {
  name                  = "ide-chat-http-redirect"
  project               = var.project_id
  target                = google_compute_target_http_proxy.https_redirect.id
  port_range            = "80"
  ip_address            = google_compute_global_address.ide_chat_ip.address
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# ── IAP access control ────────────────────────────────────────────────────────
# Grants roles/iap.httpsResourceAccessor to each member in var.iap_allowed_users.
# Members format: "user:alice@example.com", "group:devs@example.com",
#                 "domain:example.com" (entire domain)
resource "google_iap_web_backend_service_iam_member" "portal_iap_users" {
  for_each = toset(var.iap_allowed_users)

  project             = var.project_id
  web_backend_service = google_compute_backend_service.portal_backend.name
  role                = "roles/iap.httpsResourceAccessor"
  member              = each.value
}

resource "google_iap_web_backend_service_iam_member" "ide_chat_iap_users" {
  for_each = toset(var.iap_allowed_users)

  project             = var.project_id
  web_backend_service = google_compute_backend_service.ide_chat_backend.name
  role                = "roles/iap.httpsResourceAccessor"
  member              = each.value
}

# ── Allow serverless NEG to invoke Cloud Run ──────────────────────────────────
# The load balancer calls Cloud Run via the serverless robot SA.
resource "google_cloud_run_v2_service_iam_member" "portal_neg_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.portal.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_cloud_run_v2_service_iam_member" "ide_chat_neg_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ide_chat.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

# ── Allow IAP service account to invoke Cloud Run ─────────────────────────────
# IAP forwards authenticated requests to Cloud Run using its own service account.
# This SA is provisioned when IAP is first enabled via GCP Console.
resource "google_cloud_run_v2_service_iam_member" "portal_iap_sa_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.portal.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

resource "google_cloud_run_v2_service_iam_member" "ide_chat_iap_sa_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ide_chat.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}
