resource "aws_rds_cluster" "aurora_postgres" {
  cluster_identifier      = "wildfire-assessment-aurora-${var.environment}"
  engine                  = "aurora-postgresql"
  engine_version          = "15.3"
  master_username         = "root"
  master_password         = var.aurora_root_password
  database_name           = "wildfiredb"
  backup_retention_period = 7
  preferred_backup_window = "07:00-09:00"
  vpc_security_group_ids  = [aws_security_group.ecs_api.id]
  db_subnet_group_name    = aws_db_subnet_group.aurora.name

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 2
  }

  enable_http_endpoint = true

  tags = {
    Environment = var.environment
    Service     = "db"
  }
}

resource "aws_rds_cluster_instance" "aurora_postgres_instance" {
  count               = 2
  identifier          = "wildfire-assessment-aurora-instance-${var.environment}-${count.index + 1}"
  cluster_identifier  = aws_rds_cluster.aurora_postgres.id
  instance_class      = "db.serverless"
  engine              = aws_rds_cluster.aurora_postgres.engine
  engine_version      = aws_rds_cluster.aurora_postgres.engine_version
  publicly_accessible = false

  tags = {
    Environment = var.environment
    Service     = "db"
  }
}

resource "aws_db_subnet_group" "aurora" {
  name       = "wildfire-assessment-aurora-subnet-group-${var.environment}"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]

  tags = {
    Environment = var.environment
    Service     = "db"
  }
}
