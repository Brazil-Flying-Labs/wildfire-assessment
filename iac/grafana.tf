# --- Folders ---

resource "grafana_folder" "wildfire_alerts" {
  title = "Wildfire Alerts"
}

resource "grafana_folder" "wildfire_dashboards" {
  title = "Wildfire"
}

# --- Dashboards ---

resource "grafana_dashboard" "ecs" {
  folder    = grafana_folder.wildfire_dashboards.id
  overwrite = true
  config_json = file("${path.module}/grafana/ecs-dashboard.json")
}

resource "grafana_dashboard" "rds" {
  folder    = grafana_folder.wildfire_dashboards.id
  overwrite = true
  config_json = file("${path.module}/grafana/rds-dashboard.json")
}

resource "grafana_dashboard" "django" {
  folder    = grafana_folder.wildfire_dashboards.id
  overwrite = true
  config_json = file("${path.module}/grafana/django-dashboard.json")
}

resource "grafana_dashboard" "ui" {
  folder    = grafana_folder.wildfire_dashboards.id
  overwrite = true
  config_json = file("${path.module}/grafana/ui-dashboard.json")
}

resource "grafana_contact_point" "wildfire_email" {
  name = "Wildfire Team Email"

  email {
    addresses = [
      "diogo.hudson@brazilflyinglabs.org.br",
      "marcelo@brazilflyinglabs.org.br",
    ]
    subject = "{{ .Status | title }}: {{ .CommonLabels.alertname }}"
    message = "{{ len .Alerts.Firing }} firing, {{ len .Alerts.Resolved }} resolved\n\n{{ range .Alerts }}\n{{ .Annotations.summary }}\nValue: {{ .ValueString }}\n{{ end }}"
  }
}

resource "grafana_notification_policy" "wildfire" {
  contact_point   = grafana_contact_point.wildfire_email.name
  group_by        = ["grafana_folder", "alertname"]
  group_wait      = "30s"
  group_interval  = "5m"
  repeat_interval = "4h"
}

# --- RDS Alerts ---

resource "grafana_rule_group" "rds_alerts" {
  name             = "RDS Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name      = "High ACU Utilization"
    condition = "C"
    for       = "5m"

    annotations = {
      summary = "Aurora ACU utilization is above 85% — database is near its max capacity (1 ACU)."
    }

    labels = {
      severity = "warning"
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
          evaluator = { params = [85], type = "gt" }
          operator  = { type = "and" }
          query     = { params = ["C"] }
          reducer   = { params = [], type = "last" }
          type      = "query"
        }]
      })
    }
  }

  rule {
    name      = "High RDS CPU Utilization"
    condition = "C"
    for       = "5m"

    annotations = {
      summary = "Aurora CPU utilization is above 85%."
    }

    labels = {
      severity = "warning"
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
          evaluator = { params = [85], type = "gt" }
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
    name      = "High ECS CPU Usage"
    condition = "C"
    for       = "5m"

    annotations = {
      summary = "ECS service {{ $labels.dimension_ServiceName }} CPU usage is above 80%."
    }

    labels = {
      severity = "warning"
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
    name      = "High ECS Memory Usage"
    condition = "C"
    for       = "5m"

    annotations = {
      summary = "ECS service {{ $labels.dimension_ServiceName }} memory usage is above 80% — risk of OOM."
    }

    labels = {
      severity = "warning"
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

# --- UI Alerts ---

resource "grafana_rule_group" "ui_alerts" {
  name             = "UI Alerts"
  folder_uid       = grafana_folder.wildfire_alerts.uid
  interval_seconds = 300

  rule {
    name      = "Frontend JS Errors"
    condition = "C"
    for       = "0s"

    annotations = {
      summary     = "New JavaScript errors detected in the Wildfire UI."
      description = "{{ $values.B.Value }} errors in the last 5 minutes."
    }

    labels = {
      severity = "warning"
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
        expr          = "sum(count_over_time({service_name=\"wildfire-ui\", kind=\"exception\"} [5m]))"
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
