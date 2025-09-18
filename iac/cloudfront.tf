resource "aws_cloudfront_origin_access_control" "ui_website" {
  name                              = "${var.project_name}-${var.environment}-ui-oac"
  description                       = "Origin access control for ${var.project_name} UI bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "ui_website" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name}-${var.environment} UI distribution"
  default_root_object = local.ui_default_root

  origin {
    domain_name              = aws_s3_bucket.ui_website.bucket_regional_domain_name
    origin_id                = local.ui_bucket_origin_id
    origin_access_control_id = aws_cloudfront_origin_access_control.ui_website.id

    s3_origin_config {
      origin_access_identity = ""
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.ui_bucket_origin_id

    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  depends_on = [
    aws_s3_bucket_public_access_block.ui_website,
    aws_s3_bucket_ownership_controls.ui_website
  ]
}

resource "aws_s3_bucket_policy" "ui_website" {
  bucket = aws_s3_bucket.ui_website.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipalReadOnly"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action = ["s3:GetObject"]
        Resource = [
          "${aws_s3_bucket.ui_website.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.ui_website.arn
          }
        }
      }
    ]
  })
}
