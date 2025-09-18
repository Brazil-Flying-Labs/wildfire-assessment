output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_cidrs" {
  description = "CIDR blocks of the public subnets"
  value       = aws_subnet.public[*].cidr_block
}

output "private_subnet_cidrs" {
  description = "CIDR blocks of the private subnets"
  value       = aws_subnet.private[*].cidr_block
}

output "nat_gateway_ids" {
  description = "IDs of the NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_public_ips" {
  description = "Public IP addresses of the NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}

output "public_route_table_id" {
  description = "ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "IDs of the private route tables"
  value       = aws_route_table.private[*].id
}

output "availability_zones" {
  description = "List of availability zones used"
  value       = slice(data.aws_availability_zones.available.names, 0, var.az_count)
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.wildfire_assessment.repository_url
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.api.dns_name
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.api.arn
}

output "alb_listener_http_arn" {
  description = "ARN of the HTTP (80) listener"
  value       = aws_lb_listener.api_http.arn
}

output "alb_target_group_arn" {
  description = "ARN of the ALB target group for ECS"
  value       = aws_lb_target_group.api.arn
}

output "data_bucket_name" {
  description = "Name of the wildfire assessment data bucket"
  value       = aws_s3_bucket.wildfire_assessment.id
}

output "ui_bucket_name" {
  description = "Name of the UI website bucket"
  value       = aws_s3_bucket.ui_website.id
}

output "ui_bucket_domain" {
  description = "Regional domain name of the UI bucket"
  value       = aws_s3_bucket.ui_website.bucket_regional_domain_name
}

output "ui_cloudfront_domain" {
  description = "CloudFront domain for accessing the UI"
  value       = aws_cloudfront_distribution.ui_website.domain_name
}
