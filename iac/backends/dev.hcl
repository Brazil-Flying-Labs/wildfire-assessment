bucket         = "bfl-tfstate"
key            = "wildfire-assessment/dev/vpc/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "bfl-terraform-locks"
encrypt        = true
profile        = "bfl" 