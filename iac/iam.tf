############################################################
# IAM roles (task execution + task role)
############################################################
data "aws_iam_policy_document" "ecs_task_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "wildfire-assessment-exec-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_trust.json
  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "task_admin_access" {
  role       = aws_iam_role.task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_role_policy_attachment" "task_execution_policy" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task_role" {
  name               = "wildfire-assessment-task-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_trust.json
  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "grafana_cloud" {
  name        = "wildfire-assessment/${var.environment}/grafana-cloud"
  description = "Grafana Cloud credentials for ${var.environment}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy" "task_execution_secrets" {
  name = "secrets-manager-read"
  role = aws_iam_role.task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.grafana_cloud.arn
        ]
      }
    ]
  })
}
