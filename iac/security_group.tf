# resource "aws_security_group" "ecs_api" {
#   name        = "wildfire-assessment-ecs-api-${var.environment}"
#   description = "Allow inbound HTTP/HTTPS for ECS API service"
#   vpc_id      = aws_vpc.main.id # Replace with your VPC resource

#   ingress {
#     description = "Allow HTTP"
#     from_port   = 80
#     to_port     = 80
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

#   ingress {
#     description = "Allow HTTPS"
#     from_port   = 443
#     to_port     = 443
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

#   ingress {
#     description = "Allow PostgreSQL from VPC"
#     from_port   = 5432
#     to_port     = 5432
#     protocol    = "tcp"
#     cidr_blocks = [aws_vpc.main.cidr_block]
#   }

#   ingress {
#     description = "Allow ALB to access ECS task on port 10000"
#     from_port   = 10000
#     to_port     = 10000
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"] # Or restrict to ALB security group if you want more security
#   }

#   egress {
#     description = "Allow all outbound"
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }

#   tags = {
#     Environment = var.environment
#     Service     = "api"
#   }
# }
