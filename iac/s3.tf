resource "aws_s3_bucket" "wildfire_assessment" {
  bucket = "${var.project_name}-${var.environment}"
  #acl    = "private"

  tags = {
    Name        = "${var.project_name}-${var.environment}"
    Environment = "${var.environment}"
  }
}