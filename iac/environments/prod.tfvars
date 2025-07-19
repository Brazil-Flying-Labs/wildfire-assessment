# Production Environment Configuration

# AWS Configuration
aws_region  = "us-east-1"
aws_profile = "bfl"

# Project Configuration
project_name = "wildfire-assessment"
environment  = "prod"

# VPC Configuration
vpc_cidr = "10.2.0.0/16"  # Different CIDR to avoid conflicts
az_count = 3              # Higher availability for production 