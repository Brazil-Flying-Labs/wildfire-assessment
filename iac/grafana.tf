# --- Explore URLs ---

locals {
  explore_backend_errors = "${var.grafana_url}explore?orgId=1&left=${urlencode(jsonencode({
    datasource = var.grafana_loki_uid
    queries = [{
      refId     = "A"
      expr      = "{service_name=~\"wildfire-api|wildfire-celery-worker|wildfire-celery-beat\"} | detected_level=~\"error|critical\""
      queryType = "range"
    }]
    range = { from = "now-15m", to = "now" }
  }))}"

  explore_ui_errors = "${var.grafana_url}explore?orgId=1&left=${urlencode(jsonencode({
    datasource = var.grafana_loki_uid
    queries = [{
      refId     = "A"
      expr      = "{app_name=\"wildfire-ui\", kind=\"exception\"}"
      queryType = "range"
    }]
    range = { from = "now-15m", to = "now" }
  }))}"

  explore_mobile_errors = "${var.grafana_url}explore?orgId=1&left=${urlencode(jsonencode({
    datasource = var.grafana_loki_uid
    queries = [{
      refId     = "A"
      expr      = "{app_name=\"wildfire-mobile\", kind=\"exception\"}"
      queryType = "range"
    }]
    range = { from = "now-15m", to = "now" }
  }))}"
}

# --- Folders ---

resource "grafana_folder" "wildfire_alerts" {
  title = "Wildfire Alerts"
}

resource "grafana_folder" "wildfire_dashboards" {
  title = "Wildfire"
}

# --- Dashboards ---

resource "grafana_dashboard" "ecs" {
  folder      = grafana_folder.wildfire_dashboards.id
  overwrite   = true
  config_json = file("${path.module}/grafana/ecs-dashboard.json")
}

resource "grafana_dashboard" "rds" {
  folder      = grafana_folder.wildfire_dashboards.id
  overwrite   = true
  config_json = file("${path.module}/grafana/rds-dashboard.json")
}

resource "grafana_dashboard" "django" {
  folder      = grafana_folder.wildfire_dashboards.id
  overwrite   = true
  config_json = file("${path.module}/grafana/django-dashboard.json")
}

resource "grafana_dashboard" "ui" {
  folder      = grafana_folder.wildfire_dashboards.id
  overwrite   = true
  config_json = file("${path.module}/grafana/ui-dashboard.json")
}

resource "grafana_dashboard" "redis" {
  folder      = grafana_folder.wildfire_dashboards.id
  overwrite   = true
  config_json = file("${path.module}/grafana/redis-dashboard.json")
}

locals {
  alert_email_addresses = [
    "diogo.hudson@brazilflyinglabs.org.br",
    "marcelo@brazilflyinglabs.org.br",
  ]

  alert_email_message = <<-EOT
{{ range .Alerts }}
⚠️ {{ .Annotations.summary }}
{{ if .Annotations.description }}
{{ .Annotations.description }}
{{ end }}
---
{{ end }}
EOT
}

resource "grafana_contact_point" "error_alerts" {
  name = "Error Alerts (no resolve)"

  email {
    addresses               = local.alert_email_addresses
    disable_resolve_message = true
    subject                 = "{{ .CommonLabels.alertname }}"
    message                 = local.alert_email_message
  }
}

resource "grafana_contact_point" "resource_alerts" {
  name = "Resource Alerts (with resolve)"

  email {
    addresses               = local.alert_email_addresses
    disable_resolve_message = false
    subject                 = "{{ .Status | title }}: {{ .CommonLabels.alertname }}"
    message                 = local.alert_email_message
  }
}

resource "grafana_notification_policy" "wildfire" {
  contact_point   = grafana_contact_point.error_alerts.name
  group_by        = ["grafana_folder", "alertname"]
  group_wait      = "30s"
  group_interval  = "5m"
  repeat_interval = "4h"

  policy {
    contact_point = grafana_contact_point.resource_alerts.name
    matcher {
      label = "alert_type"
      match = "="
      value = "resource"
    }
    group_by        = ["grafana_folder", "alertname"]
    group_wait      = "30s"
    group_interval  = "5m"
    repeat_interval = "4h"
  }
}

# --- RDS Alerts ---

resource "grafana_rule_group" "rds_alerts" {
  name             = "RDS Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name           = "High ACU Utilization"
    condition      = "C"
    for            = "5m"
    exec_err_state = "OK"
    no_data_state  = "OK"

    annotations = {
      summary = "Aurora ACU utilization is above 95% — database is near its max capacity (1 ACU)."
    }

    labels = {
      severity   = "warning"
      alert_type = "error" # Route to contact point without resolve messages
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.grafana_prometheus_uid
      model = jsonencode({
        refId         = "A"
        expr          = "avg(aws_rds_acuutilization_average)"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "dropNN" }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [95], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }

  rule {
    name          = "High RDS CPU Utilization"
    condition     = "C"
    for           = "5m"
    no_data_state = "OK"

    annotations = {
      summary = "Aurora CPU utilization is above 95%."
    }

    labels = {
      severity   = "warning"
      alert_type = "resource"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.grafana_prometheus_uid
      model = jsonencode({
        refId         = "A"
        expr          = "avg(aws_rds_cpuutilization_average)"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "dropNN" }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [95], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }
}

# --- ECS Alerts ---

resource "grafana_rule_group" "ecs_alerts" {
  name             = "ECS Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name          = "High ECS CPU Usage"
    condition     = "C"
    for           = "5m"
    no_data_state = "OK"

    annotations = {
      summary = "ECS service {{ $labels.dimension_ServiceName }} CPU usage is above 80%."
    }

    labels = {
      severity   = "warning"
      alert_type = "resource"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.grafana_prometheus_uid
      model = jsonencode({
        refId         = "A"
        expr          = "max by (dimension_ServiceName) (aws_ecs_containerinsights_cpu_utilized_average / (aws_ecs_containerinsights_cpu_reserved_average > 0)) * 100"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "dropNN" }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [80], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }

  rule {
    name          = "High ECS Memory Usage"
    condition     = "C"
    for           = "5m"
    no_data_state = "OK"

    annotations = {
      summary = "ECS service {{ $labels.dimension_ServiceName }} memory usage is above 80% — risk of OOM."
    }

    labels = {
      severity   = "warning"
      alert_type = "resource"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.grafana_prometheus_uid
      model = jsonencode({
        refId         = "A"
        expr          = "max by (dimension_ServiceName) (aws_ecs_containerinsights_memory_utilized_average / (aws_ecs_containerinsights_memory_reserved_average > 0)) * 100"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "dropNN" }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [80], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }
}

# --- Backend Alerts ---

resource "grafana_rule_group" "backend_alerts" {
  name             = "Backend Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name          = "Backend Error Logs"
    condition     = "C"
    for           = "0s"
    no_data_state = "OK"

    annotations = {
      summary     = "{{ $values.B.Value }} error logs detected in backend services in the last 5 minutes."
      description = "View stack traces in Grafana Explore:\n${local.explore_backend_errors}"
    }

    labels = {
      severity   = "critical"
      alert_type = "error"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = var.grafana_loki_uid
      model = jsonencode({
        refId         = "A"
        expr          = "sum by (service_name) (count_over_time({service_name=~\"wildfire-api|wildfire-celery-worker|wildfire-celery-beat\", deployment_environment!=\"local\"} | detected_level=~\"error|critical\" [5m]))"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "replaceNN", replaceWithValue = 0 }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [0], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }

  rule {
    name          = "API 5xx Responses"
    condition     = "C"
    for           = "0s"
    no_data_state = "OK"

    annotations = {
      summary     = "API returned {{ $values.B.Value }} HTTP 5xx errors/sec in the last 5 minutes."
      description = "View errors in Grafana Explore:\n${local.explore_backend_errors}"
    }

    labels = {
      severity   = "critical"
      alert_type = "error"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = var.grafana_prometheus_uid
      model = jsonencode({
        refId         = "A"
        expr          = "sum(rate(http_server_duration_milliseconds_count{service_name=\"wildfire-api\", deployment_environment!=\"local\", http_status_code=~\"5..\"}[5m]))"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "replaceNN", replaceWithValue = 0 }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [0], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }
}

# --- Web UI Alerts ---

resource "grafana_rule_group" "ui_alerts" {
  name             = "Web UI Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name          = "Web UI JS Errors"
    condition     = "C"
    for           = "0s"
    no_data_state = "OK"

    annotations = {
      summary     = "{{ $values.B.Value }} JavaScript errors detected in the Wildfire Web UI in the last 5 minutes."
      description = "View errors in Grafana Explore:\n${local.explore_ui_errors}"
    }

    labels = {
      severity   = "warning"
      alert_type = "error"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = var.grafana_loki_uid
      model = jsonencode({
        refId         = "A"
        expr          = "sum(count_over_time({app_name=\"wildfire-ui\", kind=\"exception\", app_environment!=\"local\"} [5m]))"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "replaceNN", replaceWithValue = 0 }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [0], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }
}

# --- Mobile App Alerts ---

resource "grafana_rule_group" "mobile_alerts" {
  name             = "Mobile App Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name          = "Mobile App JS Errors"
    condition     = "C"
    for           = "0s"
    no_data_state = "OK"

    annotations = {
      summary     = "{{ $values.B.Value }} JavaScript errors detected in the Wildfire Mobile App in the last 5 minutes."
      description = "View errors in Grafana Explore:\n${local.explore_mobile_errors}"
    }

    labels = {
      severity   = "warning"
      alert_type = "error"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = var.grafana_loki_uid
      model = jsonencode({
        refId         = "A"
        expr          = "sum(count_over_time({app_name=\"wildfire-mobile\", kind=\"exception\", app_environment!=\"local\"} [5m]))"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "replaceNN", replaceWithValue = 0 }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 300
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [0], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }
}

# --- Redis Alerts ---

resource "grafana_rule_group" "redis_alerts" {
  name             = "Redis Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name          = "High Redis Memory"
    condition     = "C"
    for           = "5m"
    no_data_state = "OK"

    annotations = {
      summary = "Redis memory usage is above 800 MB (80% of 1 GB container limit)."
    }

    labels = {
      severity   = "warning"
      alert_type = "resource"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.grafana_prometheus_uid
      model = jsonencode({
        refId         = "A"
        expr          = "redis_memory_used_bytes"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "dropNN" }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [838860800], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }

  rule {
    name           = "Redis Down"
    condition      = "C"
    for            = "2m"
    exec_err_state = "Alerting"
    no_data_state  = "Alerting"

    annotations = {
      summary = "Redis instance is unreachable — Celery broker and Django cache are unavailable."
    }

    labels = {
      severity   = "critical"
      alert_type = "error"
    }

    data {
      ref_id = "A"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = var.grafana_prometheus_uid
      model = jsonencode({
        refId         = "A"
        expr          = "redis_up"
        intervalMs    = 1000
        maxDataPoints = 43200
      })
    }

    data {
      ref_id = "B"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "B"
        type       = "reduce"
        expression = "A"
        reducer    = "last"
        settings   = { mode = "replaceNN", replaceWithValue = 0 }
      })
    }

    data {
      ref_id = "C"
      relative_time_range {
        from = 600
        to   = 0
      }
      datasource_uid = "__expr__"
      model = jsonencode({
        refId      = "C"
        type       = "threshold"
        expression = "B"
        conditions = [{
          evaluator = { params = [1], type = "lt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }
}
