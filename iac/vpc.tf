# Data source to get available AZs
#data "aws_availability_zones" "available" {
#  state = "available"
#}

# VPC
#resource "aws_vpc" "main" {
#  cidr_block           = var.vpc_cidr
#  enable_dns_hostnames = true
#  enable_dns_support   = true

#  tags = {
#    Name        = "${var.project_name}-vpc"
#    Environment = var.environment
#  }
#}

# Internet Gateway
#resource "aws_internet_gateway" "main" {
#  vpc_id = aws_vpc.main.id

#  tags = {
#    Name        = "${var.project_name}-igw"
#    Environment = var.environment
#    Description = "Internet Gateway for ${var.project_name} in ${var.environment}"
#  }
#}

# Public Subnets
#resource "aws_subnet" "public" {
#  count = var.az_count

#  vpc_id                  = aws_vpc.main.id
#  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
#  availability_zone       = data.aws_availability_zones.available.names[count.index]
#  map_public_ip_on_launch = true

#  tags = {
#    Name        = "${var.project_name}-public-${count.index + 1}"
#    Environment = var.environment
#    Type        = "Public"
#  }
#}

# Private Subnets
#resource "aws_subnet" "private" {
#  count = var.az_count

#  vpc_id            = aws_vpc.main.id
#  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
#  availability_zone = data.aws_availability_zones.available.names[count.index]

#  tags = {
#    Name        = "${var.project_name}-private-${count.index + 1}"
#    Environment = var.environment
#    Type        = "Private"
#  }
#}

# Elastic IPs for NAT Gateways
#resource "aws_eip" "nat" {
#  count = var.az_count

#  domain = "vpc"
#  depends_on = [aws_internet_gateway.main]

#  tags = {
#    Name        = "${var.project_name}-eip-${count.index + 1}"
#    Environment = var.environment
#  }
#}

# NAT Gateways
#resource "aws_nat_gateway" "main" {
#  count = var.az_count

#  allocation_id = aws_eip.nat[count.index].id
#  subnet_id     = aws_subnet.public[count.index].id

 # tags = {
 #   Name        = "${var.project_name}-nat-${count.index + 1}"
  #  Environment = var.environment
  #}

  #depends_on = [aws_internet_gateway.main]
#}

# Route Table for Public Subnets
#resource "aws_route_table" "public" {
#  vpc_id = aws_vpc.main.id

#  route {
#    cidr_block = "0.0.0.0/0"
#    gateway_id = aws_internet_gateway.main.id
#  }

#  tags = {
#    Name        = "${var.project_name}-public-rt"
#    Environment = var.environment
#  }
#}

# Route Tables for Private Subnets
#resource "aws_route_table" "private" {
#  count = var.az_count

 # vpc_id = aws_vpc.main.id

  #route {
   # cidr_block     = "0.0.0.0/0"
    #nat_gateway_id = aws_nat_gateway.main[count.index].id
  #}

  #tags = {
   # Name        = "${var.project_name}-private-rt-${count.index + 1}"
    #Environment = var.environment
  #}
#}

# Associate Public Subnets with Public Route Table
#resource "aws_route_table_association" "public" {
 # count = var.az_count

  #subnet_id      = aws_subnet.public[count.index].id
  #route_table_id = aws_route_table.public.id
#}

# Associate Private Subnets with Private Route Tables
#resource "aws_route_table_association" "private" {
 # count = var.az_count

  #subnet_id      = aws_subnet.private[count.index].id
  #route_table_id = aws_route_table.private[count.index].id
#} 