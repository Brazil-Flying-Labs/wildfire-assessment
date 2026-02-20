locals {
  data_bucket_name    = "${var.project_name}-${var.environment}"
  ui_bucket_name      = "${var.project_name}-${var.environment}-ui"
  ui_bucket_origin_id = "ui-website-origin"
  ui_default_root     = "index.html"
  ui_error_document   = "index.html"
}

resource "aws_s3_bucket" "wildfire_assessment" {
  bucket = local.data_bucket_name

  tags = {
    Name        = local.data_bucket_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "wildfire_assessment" {
  bucket = aws_s3_bucket.wildfire_assessment.id

  rule {
    id     = "expire-objects-after-2-years"
    status = "Enabled"

    # Apply to all objects (required by provider)
    filter {}

    expiration {
      days = 730
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "wildfire_assessment" {
  bucket = aws_s3_bucket.wildfire_assessment.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = var.s3_cors_allowed_origins
    expose_headers  = []
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket" "ui_website" {
  bucket        = local.ui_bucket_name
  force_destroy = false

  tags = {
    Name        = local.ui_bucket_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "ui_website" {
  bucket                  = aws_s3_bucket.ui_website.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "ui_website" {
  bucket = aws_s3_bucket.ui_website.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_versioning" "ui_website" {
  bucket = aws_s3_bucket.ui_website.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_website_configuration" "ui_website" {
  bucket = aws_s3_bucket.ui_website.id

  index_document {
    suffix = local.ui_default_root
  }

  error_document {
    key = local.ui_error_document
  }
}
