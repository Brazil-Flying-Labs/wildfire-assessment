resource "aws_ecs_cluster" "wildfire_assessment" {
  name = "wildfire-assessment-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
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
  name        = "redis"
  namespace_id = aws_service_discovery_private_dns_namespace.ecs.id

  dns_config {
    namespace_id  = aws_service_discovery_private_dns_namespace.ecs.id
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
}


############################################################
# ECS Task Definition: API (Fargate)
############################################################
resource "aws_ecs_task_definition" "api" {
  family                   = "wildfire-assessment-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024" # 1 vCPU
  memory                   = "2048" # 2 GB (minimum for 1 vCPU on Fargate)

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

      # (Optional) Env vars
      environment = [
        { name = "ENV", value = var.environment },
        { name = "CELERY_BROKER_URL", value = local.redis_url }
      ]

      # Logs -> CloudWatch (2-day retention already set on the log group)
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
    }
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
  cpu                      = "512"
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
  cpu                      = "1024"
  memory                   = "2048"

  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn      = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "celery-worker"
      image     = "${aws_ecr_repository.wildfire_assessment.repository_url}:latest"
      essential = true
      command   = ["sh", "-c", "celery -A wildfire_assessment worker --loglevel=info"]

      environment = [
        { name = "ENV", value = var.environment },
        { name = "CELERY_BROKER_URL", value = local.redis_url }
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
    }
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
  cpu                      = "512"
  memory                   = "1024"

  execution_role_arn = aws_iam_role.task_execution.arn
  task_role_arn      = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "celery-beat"
      image     = "${aws_ecr_repository.wildfire_assessment.repository_url}:latest"
      essential = true
      command   = ["sh", "-c", "celery -A wildfire_assessment beat --loglevel=info"]

      environment = [
        { name = "ENV", value = var.environment },
        { name = "CELERY_BROKER_URL", value = local.redis_url }
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
    }
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
