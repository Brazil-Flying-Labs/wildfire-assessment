resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/wildfire-assessment-${var.environment}"
  retention_in_days = 3

  tags = {
    Name        = "ecs-wildfire-assessment-${var.environment}"
    Environment = var.environment
  }
}
