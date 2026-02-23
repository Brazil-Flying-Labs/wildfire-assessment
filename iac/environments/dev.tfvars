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

ui_domain_aliases  = ["wildfire-dev.droneai.com.br", "wildfire.droneai.com.br"]
ui_certificate_arn = "arn:aws:acm:us-east-1:055213706289:certificate/9e1e42ad-114d-4dd4-b317-7aed7735a37c"

grafana_url = "https://brazilflyinglabs.grafana.net/"
grafana_loki_uid = "grafanacloud-logs"