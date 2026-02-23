resource "aws_ecs_cluster" "wildfire_assessment" {
  name = "wildfire-assessment-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enhanced"
  }

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs.name
      }
    }
  }

  tags = {
    Name        = "wildfire-assessment-${var.environment}"
    Environment = var.environment
  }
}

# NEW: manage capacity providers here (not inside aws_ecs_cluster)
resource "aws_ecs_cluster_capacity_providers" "wildfire_assessment" {
  cluster_name       = aws_ecs_cluster.wildfire_assessment.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }
}

############################################################
# Prereqs (if not already defined elsewhere)
############################################################
data "aws_region" "current" {}

resource "aws_service_discovery_private_dns_namespace" "ecs" {
  name        = "${var.project_name}.local"
  description = "Private namespace for ${var.project_name} services"
  vpc         = aws_vpc.main.id
}

resource "aws_service_discovery_service" "redis" {
  name         = "redis"
  namespace_id = aws_service_discovery_private_dns_namespace.ecs.id

  dns_config {
    namespace_id   = aws_service_discovery_private_dns_namespace.ecs.id
    routing_policy = "MULTIVALUE"

    dns_records {
      ttl  = 10
      type = "A"
    }
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

locals {
  redis_hostname = "redis.${aws_service_discovery_private_dns_namespace.ecs.name}"
  redis_url      = "redis://${local.redis_hostname}:6379/0"

  # Inline Alloy config for ECS (passed via environment variable)
  alloy_config = <<-EOT
    otelcol.receiver.otlp "default" {
      grpc { endpoint = "0.0.0.0:4317" }
      http { endpoint = "0.0.0.0:4318" }
      output {
        metrics = [otelcol.exporter.otlphttp.grafana.input]
        logs    = [otelcol.exporter.otlphttp.grafana.input]
        traces  = [otelcol.exporter.otlphttp.grafana.input]
      }
    }
    otelcol.auth.basic "grafana" {
      username = sys.env("GRAFANA_CLOUD_INSTANCE_ID")
      password = sys.env("GRAFANA_CLOUD_API_KEY")
    }
    otelcol.exporter.otlphttp "grafana" {
      client {
        endpoint = sys.env("GRAFANA_CLOUD_OTLP_ENDPOINT")
        auth     = otelcol.auth.basic.grafana.handler
      }
    }
  EOT

  # Alloy config for API sidecar (OTLP + PostgreSQL metrics)
  alloy_config_api = <<-EOT
    otelcol.receiver.otlp "default" {
      grpc { endpoint = "0.0.0.0:4317" }
      http { endpoint = "0.0.0.0:4318" }
      output {
        metrics = [otelcol.exporter.otlphttp.grafana.input]
        logs    = [otelcol.exporter.otlphttp.grafana.input]
        traces  = [otelcol.exporter.otlphttp.grafana.input]
      }
    }
    otelcol.auth.basic "grafana" {
      username = sys.env("GRAFANA_CLOUD_INSTANCE_ID")
      password = sys.env("GRAFANA_CLOUD_API_KEY")
    }
    otelcol.exporter.otlphttp "grafana" {
      client {
        endpoint = sys.env("GRAFANA_CLOUD_OTLP_ENDPOINT")
        auth     = otelcol.auth.basic.grafana.handler
      }
    }

    prometheus.exporter.postgres "rds" {
      data_source_names = [sys.env("RDS_DSN")]
    }

    prometheus.scrape "postgres" {
      targets         = prometheus.exporter.postgres.rds.targets
      forward_to      = [prometheus.remote_write.grafana.receiver]
      scrape_interval = "60s"
    }

    prometheus.exporter.cloudwatch "aurora" {
      sts_region = "us-east-1"

      discovery {
        type    = "AWS/RDS"
        regions = ["us-east-1"]

        search_tags = {
          "Environment" = sys.env("ENVIRONMENT"),
        }

        metric {
          name       = "CPUUtilization"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "FreeableMemory"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "DatabaseConnections"
          statistics = ["Sum"]
          period     = "5m"
        }
        metric {
          name       = "ServerlessDatabaseCapacity"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "ACUUtilization"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "ReadIOPS"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "WriteIOPS"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "ReadLatency"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "WriteLatency"
          statistics = ["Average"]
          period     = "5m"
        }
      }
    }

    prometheus.exporter.cloudwatch "ecs" {
      sts_region = "us-east-1"

      discovery {
        type    = "ECS/ContainerInsights"
        regions = ["us-east-1"]

        search_tags = {
          "Environment" = sys.env("ENVIRONMENT"),
        }

        metric {
          name       = "CpuUtilized"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "CpuReserved"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "MemoryUtilized"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "MemoryReserved"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "NetworkRxBytes"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "NetworkTxBytes"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "StorageReadBytes"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "StorageWriteBytes"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "RunningTaskCount"
          statistics = ["Average"]
          period     = "5m"
        }
        metric {
          name       = "DesiredTaskCount"
          statistics = ["Average"]
          period     = "5m"
        }
      }
    }

    prometheus.scrape "cloudwatch_aurora" {
      targets         = prometheus.exporter.cloudwatch.aurora.targets
      forward_to      = [prometheus.remote_write.grafana.receiver]
      scrape_interval = "5m"
    }

    prometheus.scrape "cloudwatch_ecs" {
      targets         = prometheus.exporter.cloudwatch.ecs.targets
      forward_to      = [prometheus.remote_write.grafana.receiver]
      scrape_interval = "5m"
    }

    prometheus.remote_write "grafana" {
      endpoint {
        url = sys.env("GRAFANA_CLOUD_PROMETHEUS_PUSH_URL")
        basic_auth {
          username = sys.env("GRAFANA_CLOUD_PROMETHEUS_USERNAME")
          password = sys.env("GRAFANA_CLOUD_PROMETHEUS_PASSWORD")
        }
      }
    }
  EOT

  # Alloy sidecar for API task (OTLP + PostgreSQL + CloudWatch metrics)
  alloy_sidecar_api = {
    name      = "grafana-alloy"
    image     = "grafana/alloy:v1.8.0"
    essential = false

    portMappings = [
      { containerPort = 4317, protocol = "tcp" },
      { containerPort = 4318, protocol = "tcp" }
    ]

    entryPoint = ["/bin/sh", "-c"]
    command    = ["export RDS_DSN=\"postgresql://$${DB_USERNAME}:$${DB_PASSWORD}@$${DB_HOST}:5432/$${DB_NAME}?sslmode=require\" && printenv ALLOY_CONFIG_CONTENT > /tmp/config.alloy && exec /bin/alloy run --server.http.listen-addr=0.0.0.0:12345 /tmp/config.alloy"]

    environment = [
      { name = "ALLOY_CONFIG_CONTENT", value = local.alloy_config_api },
      { name = "ENVIRONMENT", value = var.environment }
    ]

    secrets = [
      {
        name      = "GRAFANA_CLOUD_INSTANCE_ID"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_INSTANCE_ID::"
      },
      {
        name      = "GRAFANA_CLOUD_API_KEY"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_API_KEY::"
      },
      {
        name      = "GRAFANA_CLOUD_OTLP_ENDPOINT"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_OTLP_ENDPOINT::"
      },
      {
        name      = "DB_USERNAME"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:DB_USERNAME::"
      },
      {
        name      = "DB_PASSWORD"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:DB_PASSWORD::"
      },
      {
        name      = "DB_HOST"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:DB_HOST::"
      },
      {
        name      = "DB_NAME"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:DB_NAME::"
      },
      {
        name      = "GRAFANA_CLOUD_PROMETHEUS_PUSH_URL"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_PROMETHEUS_PUSH_URL::"
      },
      {
        name      = "GRAFANA_CLOUD_PROMETHEUS_USERNAME"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_PROMETHEUS_USERNAME::"
      },
      {
        name      = "GRAFANA_CLOUD_PROMETHEUS_PASSWORD"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_PROMETHEUS_PASSWORD::"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "alloy"
      }
    }
  }

  # Shared Grafana Alloy sidecar (receives OTLP, forwards to Grafana Cloud)
  alloy_sidecar = {
    name      = "grafana-alloy"
    image     = "grafana/alloy:v1.8.0"
    essential = false

    portMappings = [
      { containerPort = 4317, protocol = "tcp" },
      { containerPort = 4318, protocol = "tcp" }
    ]

    entryPoint = ["/bin/sh", "-c"]
    command    = ["printenv ALLOY_CONFIG_CONTENT > /tmp/config.alloy && exec /bin/alloy run --server.http.listen-addr=0.0.0.0:12345 /tmp/config.alloy"]

    environment = [
      { name = "ALLOY_CONFIG_CONTENT", value = local.alloy_config }
    ]

    secrets = [
      {
        name      = "GRAFANA_CLOUD_INSTANCE_ID"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_INSTANCE_ID::"
      },
      {
        name      = "GRAFANA_CLOUD_API_KEY"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_API_KEY::"
      },
      {
        name      = "GRAFANA_CLOUD_OTLP_ENDPOINT"
        valueFrom = "${data.aws_secretsmanager_secret.env.arn}:GRAFANA_CLOUD_OTLP_ENDPOINT::"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "alloy"
      }
    }
  }
}


############################################################
# ECS Task Definition: API (Fargate)
############################################################
resource "aws_ecs_task_definition" "api" {
  family                   = "wildfire-assessment-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"  # 0.5 vCPU (needs CPU headroom for startup + request handling)
  memory                   = "2048" # 2 GB

  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn      = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.wildfire_assessment.repository_url}:latest"
      essential = true

      portMappings = [
        { containerPort = 10000, protocol = "tcp" }
      ]

      environment = [
        { name = "ENV", value = var.environment },
        { name = "DJANGO_SETTINGS_MODULE", value = "api.settings" },
        { name = "CELERY_BROKER_URL", value = local.redis_url },
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4318" },
        { name = "OTEL_EXPORTER_OTLP_PROTOCOL", value = "http/protobuf" },
        { name = "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED", value = "true" },
        { name = "OTEL_LOGS_EXPORTER", value = "otlp" },
        { name = "OTEL_RESOURCE_ATTRIBUTES", value = "service.name=wildfire-api,service.namespace=wildfire-assessment,deployment.environment=${var.environment}" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "api"
        }
      }

      linuxParameters = {
        initProcessEnabled = true
      }
    },
    local.alloy_sidecar_api
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = {
    Environment = var.environment
    Service     = "api"
  }
}


resource "aws_ecs_service" "api" {
  name            = "wildfire-assessment-api-${var.environment}"
  cluster         = aws_ecs_cluster.wildfire_assessment.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1

  network_configuration {
    subnets          = [for subnet in aws_subnet.private : subnet.id]
    security_groups  = [aws_security_group.ecs_api.id]
    assign_public_ip = false
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 10000
  }

  tags = {
    Environment = var.environment
    Service     = "api"
  }
}

############################################################
# ECS Task Definition: Redis (Fargate)
############################################################
resource "aws_ecs_task_definition" "redis" {
  family                   = "wildfire-assessment-redis-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "1024"

  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn      = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "redis"
      image     = "redis:7-alpine"
      essential = true

      portMappings = [
        { containerPort = 6379, protocol = "tcp" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "redis"
        }
      }
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = {
    Environment = var.environment
    Service     = "redis"
  }
}

resource "aws_ecs_service" "redis" {
  name            = "wildfire-assessment-redis-${var.environment}"
  cluster         = aws_ecs_cluster.wildfire_assessment.id
  task_definition = aws_ecs_task_definition.redis.arn
  desired_count   = 1

  network_configuration {
    subnets          = [for subnet in aws_subnet.private : subnet.id]
    security_groups  = [aws_security_group.redis.id]
    assign_public_ip = false
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }

  service_registries {
    registry_arn = aws_service_discovery_service.redis.arn
  }

  tags = {
    Environment = var.environment
    Service     = "redis"
  }
}

############################################################
# ECS Task Definition: Celery Worker
############################################################
resource "aws_ecs_task_definition" "celery_worker" {
  family                   = "wildfire-assessment-celery-worker-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "2048"

  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn      = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "celery-worker"
      image     = "${aws_ecr_repository.wildfire_assessment.repository_url}:latest"
      essential = true
      command   = ["sh", "-c", "opentelemetry-instrument celery -A wildfire_assessment worker --loglevel=info --concurrency=10"]

      environment = [
        { name = "ENV", value = var.environment },
        { name = "DJANGO_SETTINGS_MODULE", value = "api.settings" },
        { name = "CELERY_BROKER_URL", value = local.redis_url },
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4318" },
        { name = "OTEL_EXPORTER_OTLP_PROTOCOL", value = "http/protobuf" },
        { name = "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED", value = "true" },
        { name = "OTEL_LOGS_EXPORTER", value = "otlp" },
        { name = "OTEL_RESOURCE_ATTRIBUTES", value = "service.name=wildfire-celery-worker,service.namespace=wildfire-assessment,deployment.environment=${var.environment}" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "celery-worker"
        }
      }

      linuxParameters = {
        initProcessEnabled = true
      }
    },
    local.alloy_sidecar
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = {
    Environment = var.environment
    Service     = "celery-worker"
  }
}

resource "aws_ecs_service" "celery_worker" {
  name            = "wildfire-assessment-celery-worker-${var.environment}"
  cluster         = aws_ecs_cluster.wildfire_assessment.id
  task_definition = aws_ecs_task_definition.celery_worker.arn
  desired_count   = 1

  network_configuration {
    subnets          = [for subnet in aws_subnet.private : subnet.id]
    security_groups  = [aws_security_group.ecs_api.id]
    assign_public_ip = false
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }

  tags = {
    Environment = var.environment
    Service     = "celery-worker"
  }
}

############################################################
# ECS Task Definition: Celery Beat
############################################################
resource "aws_ecs_task_definition" "celery_beat" {
  family                   = "wildfire-assessment-celery-beat-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "1024"

  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn      = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "celery-beat"
      image     = "${aws_ecr_repository.wildfire_assessment.repository_url}:latest"
      essential = true
      command   = ["sh", "-c", "opentelemetry-instrument celery -A wildfire_assessment beat --loglevel=info"]

      environment = [
        { name = "ENV", value = var.environment },
        { name = "DJANGO_SETTINGS_MODULE", value = "api.settings" },
        { name = "CELERY_BROKER_URL", value = local.redis_url },
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4318" },
        { name = "OTEL_EXPORTER_OTLP_PROTOCOL", value = "http/protobuf" },
        { name = "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED", value = "true" },
        { name = "OTEL_LOGS_EXPORTER", value = "otlp" },
        { name = "OTEL_RESOURCE_ATTRIBUTES", value = "service.name=wildfire-celery-beat,service.namespace=wildfire-assessment,deployment.environment=${var.environment}" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "celery-beat"
        }
      }

      linuxParameters = {
        initProcessEnabled = true
      }
    },
    local.alloy_sidecar
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = {
    Environment = var.environment
    Service     = "celery-beat"
  }
}

resource "aws_ecs_service" "celery_beat" {
  name            = "wildfire-assessment-celery-beat-${var.environment}"
  cluster         = aws_ecs_cluster.wildfire_assessment.id
  task_definition = aws_ecs_task_definition.celery_beat.arn
  desired_count   = 1

  network_configuration {
    subnets          = [for subnet in aws_subnet.private : subnet.id]
    security_groups  = [aws_security_group.ecs_api.id]
    assign_public_ip = false
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 0
  }

  tags = {
    Environment = var.environment
    Service     = "celery-beat"
  }
}
