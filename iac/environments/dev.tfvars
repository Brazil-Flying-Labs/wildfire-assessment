# Development Environment Configuration

# AWS Configuration
aws_region  = "us-east-1"
aws_profile = "bfl"

# Project Configuration
project_name = "wildfire-assessment"
environment  = "dev"

# VPC Configuration
vpc_cidr = "10.0.0.0/16"
az_count = 2 

ui_domain_aliases  = ["wildfire-dev.droneai.com.br"]
ui_certificate_arn = "arn:aws:acm:us-east-1:055213706289:certificate/7895e08e-00c7-474e-9e04-10b7784bf753"