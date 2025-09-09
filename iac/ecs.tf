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


############################################################
# ECS Task Definition: API (Fargate)
############################################################
resource "aws_ecs_task_definition" "api" {
  family                   = "wildfire-assessment-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"  # 0.5 vCPU
  memory                   = "1024" # 1 GB

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
        { name = "ENVIRONMENT", value = var.environment }
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
