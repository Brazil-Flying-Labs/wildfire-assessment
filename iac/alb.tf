# Create the ALB
resource "aws_lb" "api" {
  name               = "wildfire-assessment-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.ecs_api.id]
  subnets            = [for subnet in aws_subnet.public : subnet.id]

  tags = {
    Environment = var.environment
    Service     = "api"
  }
}

# Target group for ECS service
resource "aws_lb_target_group" "api" {
  name        = "wildfire-assessment-tg-${var.environment}"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check {
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Environment = var.environment
    Service     = "api"
  }
}


resource "aws_lb_listener" "api_http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
