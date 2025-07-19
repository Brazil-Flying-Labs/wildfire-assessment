# Configure the AWS Provider
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0"
  
  backend "s3" {
    # Backend configuration will be provided via backend config files
    # or command line arguments during terraform init
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

