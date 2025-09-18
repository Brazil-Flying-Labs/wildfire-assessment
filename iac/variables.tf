variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS profile to use for authentication"
  type        = string
  default     = null
}

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
  default     = "wildfire-assessment"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "s3_cors_allowed_origins" {
  description = "List of origins allowed to access public assets in the S3 bucket"
  type        = list(string)
  default     = ["http://localhost:3000", "https://d3o6p3bj2dy1t.cloudfront.net/"]
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of Availability Zones to use"
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 6
    error_message = "The az_count value must be between 2 and 6."
  }
}
