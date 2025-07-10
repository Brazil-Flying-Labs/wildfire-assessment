# AWS RDS PostgreSQL + PostGIS Setup Guide (Production)

## Overview

This guide covers setting up AWS RDS PostgreSQL with PostGIS extension for production deployment in Brazil. This configuration ensures data residency compliance and optimal performance for the Wildfire Assessment Platform.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- AWS CDK v2 installed
- Basic understanding of VPC networking

## Architecture Overview

```
Internet Gateway
    │
    ├── Public Subnet (NAT Gateway)
    └── Private Subnet (RDS Database)
        │
        ├── Database Security Group
        └── Application Security Group
```

## Step 1: Regional Considerations

### AWS São Paulo Region (sa-east-1)
- **Availability Zones**: sa-east-1a, sa-east-1b, sa-east-1c
- **Data Residency**: Complies with Brazilian data protection laws
- **Latency**: ~10-30ms for users in Brazil
- **Compliance**: LGPD (Lei Geral de Proteção de Dados) compatible

### Service Availability Check
```bash
# Verify RDS availability in São Paulo
aws rds describe-orderable-db-instance-options \
  --engine postgres \
  --region sa-east-1 \
  --query 'OrderableDBInstanceOptions[?EngineVersion==`13.7`].[DBInstanceClass,StorageType]' \
  --output table
```

## Step 2: VPC and Networking Setup

### VPC Configuration (CDK)

```typescript
// lib/vpc-stack.ts
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as cdk from 'aws-cdk-lib'

export class VpcStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc
  public readonly databaseSecurityGroup: ec2.SecurityGroup

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props)

    // Create VPC in São Paulo
    this.vpc = new ec2.Vpc(this, 'WildfireVPC', {
      maxAzs: 3,
      cidr: '10.0.0.0/16',
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
        {
          name: 'database',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 28,
        },
      ],
    })

    // Database security group
    this.databaseSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for RDS PostgreSQL database',
      allowAllOutbound: false,
    })

    // Application security group (for Lambda/ECS)
    const appSecurityGroup = new ec2.SecurityGroup(this, 'ApplicationSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for application servers',
    })

    // Allow database access from application layer
    this.databaseSecurityGroup.addIngressRule(
      appSecurityGroup,
      ec2.Port.tcp(5432),
      'Allow PostgreSQL access from application layer'
    )

    // Allow HTTPS outbound for updates
    this.databaseSecurityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS outbound for updates'
    )
  }
}
```

## Step 3: RDS Database Setup

### Database Configuration (CDK)

```typescript
// lib/database-stack.ts
import * as rds from 'aws-cdk-lib/aws-rds'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager'
import * as cdk from 'aws-cdk-lib'

export interface DatabaseStackProps extends cdk.StackProps {
  vpc: ec2.Vpc
  databaseSecurityGroup: ec2.SecurityGroup
}

export class DatabaseStack extends cdk.Stack {
  public readonly database: rds.DatabaseInstance
  public readonly databaseSecret: secretsmanager.Secret

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props)

    // Create database credentials secret
    this.databaseSecret = new secretsmanager.Secret(this, 'DatabaseSecret', {
      secretName: 'wildfire-assessment/database/master',
      description: 'Master credentials for wildfire assessment database',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({ username: 'postgres' }),
        generateStringKey: 'password',
        excludeCharacters: '"@/\\\'',
      },
    })

    // Create DB subnet group
    const subnetGroup = new rds.SubnetGroup(this, 'DatabaseSubnetGroup', {
      description: 'Subnet group for wildfire assessment database',
      vpc: props.vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      },
    })

    // Create parameter group for PostgreSQL optimization
    const parameterGroup = new rds.ParameterGroup(this, 'DatabaseParameterGroup', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_13_7,
      }),
      description: 'Parameter group for wildfire assessment PostgreSQL',
      parameters: {
        // Optimize for spatial workloads
        shared_preload_libraries: 'postgis',
        max_connections: '200',
        shared_buffers: '256MB',
        effective_cache_size: '1GB',
        maintenance_work_mem: '64MB',
        checkpoint_completion_target: '0.9',
        wal_buffers: '16MB',
        default_statistics_target: '100',
        random_page_cost: '1.1',
        effective_io_concurrency: '200',
        work_mem: '4MB',
        min_wal_size: '1GB',
        max_wal_size: '4GB',
      },
    })

    // Create RDS instance
    this.database = new rds.DatabaseInstance(this, 'Database', {
      instanceIdentifier: 'wildfire-assessment-prod',
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_13_7,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
      
      // Storage configuration
      allocatedStorage: 500,
      maxAllocatedStorage: 1000,
      storageType: rds.StorageType.GP2,
      storageEncrypted: true,
      
      // Network configuration
      vpc: props.vpc,
      subnetGroup,
      securityGroups: [props.databaseSecurityGroup],
      port: 5432,
      
      // High availability
      multiAz: true,
      availabilityZone: 'sa-east-1a',
      
      // Backup configuration
      backupRetention: cdk.Duration.days(7),
      deleteAutomatedBackups: false,
      deletionProtection: true,
      
      // Credentials
      credentials: rds.Credentials.fromSecret(this.databaseSecret),
      databaseName: 'wildfire_assessment',
      
      // Monitoring
      monitoringInterval: cdk.Duration.seconds(60),
      enablePerformanceInsights: true,
      
      // Parameter group
      parameterGroup,
      
      // Maintenance
      autoMinorVersionUpgrade: true,
      preferredBackupWindow: '03:00-04:00', // 12 AM - 1 AM Brazil time
      preferredMaintenanceWindow: 'sun:04:00-sun:05:00', // 1 AM - 2 AM Brazil time
      
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    })

    // Output connection information
    new cdk.CfnOutput(this, 'DatabaseEndpoint', {
      value: this.database.instanceEndpoint.hostname,
      description: 'RDS PostgreSQL endpoint',
    })

    new cdk.CfnOutput(this, 'DatabasePort', {
      value: this.database.instanceEndpoint.port.toString(),
      description: 'RDS PostgreSQL port',
    })
  }
}
```

## Step 4: PostGIS Extension Setup

### Database Initialization Script

```sql
-- init-database.sql
-- Run this after RDS instance is created

-- Connect as master user
\c wildfire_assessment

-- Create PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Create application user
CREATE USER app_user WITH PASSWORD 'secure_app_password';

-- Create application database
CREATE DATABASE wildfire_assessment_app OWNER app_user;

-- Grant permissions
\c wildfire_assessment_app

-- Grant PostGIS permissions to app user
GRANT USAGE ON SCHEMA public TO app_user;
GRANT CREATE ON SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Set up default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;

-- Verify PostGIS installation
SELECT PostGIS_version();
```

### Automated Database Setup (Lambda)

```typescript
// lib/database-init-lambda.ts
import * as lambda from 'aws-cdk-lib/aws-lambda'
import * as iam from 'aws-cdk-lib/aws-iam'
import * as cr from 'aws-cdk-lib/custom-resources'

export class DatabaseInitLambda extends Construct {
  constructor(scope: Construct, id: string, props: {
    database: rds.DatabaseInstance
    vpc: ec2.Vpc
    databaseSecret: secretsmanager.Secret
  }) {
    super(scope, id)

    // Lambda function for database initialization
    const initFunction = new lambda.Function(this, 'DatabaseInitFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      vpc: props.vpc,
      timeout: cdk.Duration.minutes(5),
      code: lambda.Code.fromInline(`
import json
import psycopg2
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    try:
        # Get database credentials from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        secret_response = secrets_client.get_secret_value(
            SecretId=event['SecretArn']
        )
        secret = json.loads(secret_response['SecretString'])
        
        # Connect to database
        conn = psycopg2.connect(
            host=event['DatabaseHost'],
            port=5432,
            database='postgres',
            user=secret['username'],
            password=secret['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Install PostGIS extensions
        extensions = [
            'CREATE EXTENSION IF NOT EXISTS postgis;',
            'CREATE EXTENSION IF NOT EXISTS postgis_topology;',
            'CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;',
            'CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;'
        ]
        
        for ext in extensions:
            cursor.execute(ext)
            logger.info(f"Executed: {ext}")
        
        # Verify PostGIS
        cursor.execute("SELECT PostGIS_version();")
        version = cursor.fetchone()[0]
        logger.info(f"PostGIS version: {version}")
        
        cursor.close()
        conn.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Database initialized successfully',
                'postgis_version': version
            })
        }
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
      `),
    })

    // Grant permissions to access secrets and VPC
    initFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: [props.databaseSecret.secretArn],
    }))

    // Custom resource to trigger initialization
    new cr.AwsCustomResource(this, 'DatabaseInit', {
      onCreate: {
        service: 'Lambda',
        action: 'invoke',
        parameters: {
          FunctionName: initFunction.functionName,
          Payload: JSON.stringify({
            DatabaseHost: props.database.instanceEndpoint.hostname,
            SecretArn: props.databaseSecret.secretArn,
          }),
        },
        physicalResourceId: cr.PhysicalResourceId.of('database-init'),
      },
      policy: cr.AwsCustomResourcePolicy.fromSdkCalls({
        resources: cr.AwsCustomResourcePolicy.ANY_RESOURCE,
      }),
    })
  }
}
```

## Step 5: Application Schema Setup

### Create Schema Migration

```sql
-- V1__create_base_schema.sql

-- Organizations table
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  country_code CHAR(2) DEFAULT 'BR',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table (extends basic auth)
CREATE TABLE app_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  full_name VARCHAR(255),
  organization_id UUID REFERENCES organizations(id),
  role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'analyst', 'user')),
  is_active BOOLEAN DEFAULT true,
  last_login TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects table with spatial data
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  area_name VARCHAR(100), -- e.g., "luiz-antonio", "cerrado"
  study_area GEOMETRY(Polygon, 4326),
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'processing')),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES app_users(id),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Satellite images metadata
CREATE TABLE satellite_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  capture_date DATE NOT NULL,
  image_type VARCHAR(50) NOT NULL CHECK (image_type IN ('rgb', 'ndvi', 'nbr', 'composite', 'severity')),
  
  -- S3 storage information
  s3_bucket VARCHAR(255) NOT NULL,
  s3_key VARCHAR(500) NOT NULL,
  file_size_bytes BIGINT,
  
  -- Processing information
  processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
  quality_score DECIMAL(3,2) CHECK (quality_score >= 0 AND quality_score <= 1),
  cloud_coverage DECIMAL(5,2) CHECK (cloud_coverage >= 0 AND cloud_coverage <= 100),
  
  -- Spatial metadata
  spatial_extent GEOMETRY(Polygon, 4326),
  pixel_resolution_meters DECIMAL(10,2),
  
  -- Additional metadata
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  UNIQUE(project_id, capture_date, image_type)
);

-- Analysis results
CREATE TABLE analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  analysis_type VARCHAR(50) NOT NULL CHECK (analysis_type IN ('ndvi', 'nbr', 'burn_severity', 'temporal_comparison', 'change_detection')),
  
  -- Input data
  input_images UUID[] NOT NULL,
  comparison_date_range DATERANGE,
  
  -- Results
  result_data JSONB NOT NULL,
  processing_parameters JSONB DEFAULT '{}',
  
  -- Output files
  output_files JSONB DEFAULT '{}',
  
  -- Statistics
  total_area_hectares DECIMAL(15,2),
  burned_area_hectares DECIMAL(15,2),
  severity_distribution JSONB, -- JSON object with severity level counts
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES app_users(id)
);

-- User project permissions
CREATE TABLE user_project_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
  granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  granted_by UUID REFERENCES app_users(id),
  expires_at TIMESTAMP WITH TIME ZONE,
  
  UNIQUE(user_id, project_id)
);

-- Processing jobs queue
CREATE TABLE processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('satellite_download', 'ndvi_calculation', 'nbr_calculation', 'burn_analysis', 'export_data')),
  
  status VARCHAR(20) DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
  priority INTEGER DEFAULT 0,
  
  -- Job configuration
  parameters JSONB NOT NULL,
  
  -- Results and logging
  result JSONB,
  error_message TEXT,
  log_s3_key VARCHAR(500),
  
  -- Timing
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  estimated_duration_seconds INTEGER,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES app_users(id)
);

-- Data exports tracking
CREATE TABLE data_exports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  export_type VARCHAR(50) NOT NULL CHECK (export_type IN ('geotiff', 'csv', 'geojson', 'pdf_report')),
  
  -- Export configuration
  date_range DATERANGE NOT NULL,
  include_types VARCHAR(100)[], -- Array of data types to include
  format_options JSONB DEFAULT '{}',
  
  -- Output
  s3_bucket VARCHAR(255),
  s3_key VARCHAR(500),
  file_size_bytes BIGINT,
  download_count INTEGER DEFAULT 0,
  
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'expired')),
  expires_at TIMESTAMP WITH TIME ZONE,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES app_users(id)
);
```

### Create Indexes

```sql
-- V2__create_indexes.sql

-- Spatial indexes
CREATE INDEX idx_projects_study_area ON projects USING GIST (study_area);
CREATE INDEX idx_satellite_images_spatial_extent ON satellite_images USING GIST (spatial_extent);

-- Time-based indexes
CREATE INDEX idx_satellite_images_capture_date ON satellite_images (capture_date);
CREATE INDEX idx_satellite_images_project_date ON satellite_images (project_id, capture_date);
CREATE INDEX idx_analysis_results_created_at ON analysis_results (created_at);

-- Status and lookup indexes
CREATE INDEX idx_satellite_images_status ON satellite_images (processing_status);
CREATE INDEX idx_processing_jobs_status_priority ON processing_jobs (status, priority DESC, created_at);
CREATE INDEX idx_processing_jobs_project ON processing_jobs (project_id, status);

-- Permission indexes
CREATE INDEX idx_user_permissions_user ON user_project_permissions (user_id);
CREATE INDEX idx_user_permissions_project ON user_project_permissions (project_id);

-- Text search indexes
CREATE INDEX idx_projects_name_trgm ON projects USING gin (name gin_trgm_ops);
CREATE INDEX idx_projects_description_trgm ON projects USING gin (description gin_trgm_ops);

-- JSONB indexes for metadata queries
CREATE INDEX idx_satellite_images_metadata ON satellite_images USING gin (metadata);
CREATE INDEX idx_analysis_results_result_data ON analysis_results USING gin (result_data);
```

## Step 6: Environment Configuration

### Production Environment Variables

```env
# Database Configuration
DATABASE_URL=postgresql://app_user:password@wildfire-assessment-prod.xyz.sa-east-1.rds.amazonaws.com:5432/wildfire_assessment_app
DB_HOST=wildfire-assessment-prod.xyz.sa-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=wildfire_assessment_app
DB_USER=app_user
DB_PASSWORD=secure_app_password
DB_SSL_MODE=require

# AWS Configuration
AWS_REGION=sa-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# S3 Configuration
S3_BUCKET_IMAGES=wildfire-assessment-images-prod
S3_BUCKET_EXPORTS=wildfire-assessment-exports-prod

# Application Configuration
NODE_ENV=production
NEXT_PUBLIC_API_BASE=https://api.wildfire-assessment.com
JWT_SECRET=your_jwt_secret

# Monitoring
SENTRY_DSN=your_sentry_dsn
LOG_LEVEL=info
```

### Connection Pool Configuration

```python
# config/database.py
import os
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

def create_production_engine():
    """Create optimized database engine for production"""
    
    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME'),
        query={
            'sslmode': 'require',
            'connect_timeout': '10',
            'application_name': 'wildfire-assessment'
        }
    )
    
    engine = create_engine(
        db_url,
        # Connection pool settings
        poolclass=pool.QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_recycle=3600,  # 1 hour
        pool_pre_ping=True,
        
        # Performance settings
        echo=False,
        echo_pool=False,
        
        # Connection arguments
        connect_args={
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
    )
    
    return engine
```

## Step 7: Monitoring and Maintenance

### CloudWatch Alarms

```typescript
// lib/monitoring-stack.ts
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch'
import * as sns from 'aws-cdk-lib/aws-sns'

export class DatabaseMonitoringStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: {
    database: rds.DatabaseInstance
  }) {
    super(scope, id)

    // SNS topic for alerts
    const alertTopic = new sns.Topic(this, 'DatabaseAlerts', {
      displayName: 'Wildfire Assessment Database Alerts',
    })

    // CPU utilization alarm
    const cpuAlarm = new cloudwatch.Alarm(this, 'DatabaseCPUAlarm', {
      metric: props.database.metricCPUUtilization(),
      threshold: 80,
      evaluationPeriods: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    })
    cpuAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(alertTopic))

    // Connection count alarm
    const connectionAlarm = new cloudwatch.Alarm(this, 'DatabaseConnectionAlarm', {
      metric: props.database.metricDatabaseConnections(),
      threshold: 150,
      evaluationPeriods: 2,
    })
    connectionAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(alertTopic))

    // Free storage space alarm
    const storageAlarm = new cloudwatch.Alarm(this, 'DatabaseStorageAlarm', {
      metric: props.database.metricFreeStorageSpace(),
      threshold: 10 * 1024 * 1024 * 1024, // 10 GB in bytes
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      evaluationPeriods: 1,
    })
    storageAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(alertTopic))
  }
}
```

### Backup Strategy

```sql
-- Automated backup verification
CREATE OR REPLACE FUNCTION verify_backup_integrity()
RETURNS TABLE(
  table_name TEXT,
  row_count BIGINT,
  last_updated TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    t.table_name::TEXT,
    (
      SELECT COUNT(*)::BIGINT 
      FROM information_schema.tables ist 
      WHERE ist.table_name = t.table_name
    ) as row_count,
    NOW() as last_updated
  FROM information_schema.tables t
  WHERE t.table_schema = 'public' 
    AND t.table_type = 'BASE TABLE';
END;
$$ LANGUAGE plpgsql;

-- Run weekly backup verification
SELECT * FROM verify_backup_integrity();
```

## Step 8: Security Configuration

### Database Security Checklist

```sql
-- 1. Create read-only user for reporting
CREATE USER readonly_user WITH PASSWORD 'readonly_secure_password';
GRANT CONNECT ON DATABASE wildfire_assessment_app TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- 2. Create backup user
CREATE USER backup_user WITH PASSWORD 'backup_secure_password';
GRANT CONNECT ON DATABASE wildfire_assessment_app TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;

-- 3. Revoke unnecessary permissions
REVOKE ALL ON SCHEMA information_schema FROM PUBLIC;
REVOKE ALL ON SCHEMA pg_catalog FROM PUBLIC;

-- 4. Enable row level security where needed
ALTER TABLE user_project_permissions ENABLE ROW LEVEL SECURITY;

-- 5. Audit sensitive operations
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  operation_type TEXT NOT NULL CHECK (operation_type IN ('INSERT', 'UPDATE', 'DELETE')),
  user_id UUID,
  old_values JSONB,
  new_values JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### IAM Policies for Application Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RDSAccess",
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBClusters"
      ],
      "Resource": [
        "arn:aws:rds:sa-east-1:*:db:wildfire-assessment-prod"
      ]
    },
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:sa-east-1:*:secret:wildfire-assessment/database/master-*"
      ]
    }
  ]
}
```

## Step 9: Migration and Deployment

### Deployment Script

```bash
#!/bin/bash
# deploy-database.sh

set -e

echo "Deploying Wildfire Assessment Database Infrastructure..."

# 1. Deploy VPC
npx cdk deploy WildfireVpcStack --region sa-east-1

# 2. Deploy Database
npx cdk deploy WildfireDatabaseStack --region sa-east-1

# 3. Wait for database to be available
echo "Waiting for database to be available..."
aws rds wait db-instance-available \
  --db-instance-identifier wildfire-assessment-prod \
  --region sa-east-1

# 4. Initialize database schema
echo "Initializing database schema..."
python scripts/init_database.py

# 5. Deploy monitoring
npx cdk deploy WildfireMonitoringStack --region sa-east-1

echo "Database deployment completed successfully!"
```

### Data Migration from Development

```python
# scripts/migrate_data.py
import os
import psycopg2
import json
from datetime import datetime

def migrate_supabase_to_rds():
    """Migrate data from Supabase to AWS RDS"""
    
    # Source (Supabase)
    source_conn = psycopg2.connect(
        host=os.getenv('SUPABASE_HOST'),
        database=os.getenv('SUPABASE_DB'),
        user=os.getenv('SUPABASE_USER'),
        password=os.getenv('SUPABASE_PASSWORD')
    )
    
    # Target (RDS)
    target_conn = psycopg2.connect(
        host=os.getenv('RDS_HOST'),
        database=os.getenv('RDS_DB'),
        user=os.getenv('RDS_USER'),
        password=os.getenv('RDS_PASSWORD')
    )
    
    tables_to_migrate = [
        'organizations',
        'projects',
        'satellite_images',
        'analysis_results',
        'user_project_permissions'
    ]
    
    for table in tables_to_migrate:
        print(f"Migrating table: {table}")
        
        # Extract data
        source_cursor = source_conn.cursor()
        source_cursor.execute(f"SELECT * FROM {table}")
        rows = source_cursor.fetchall()
        columns = [desc[0] for desc in source_cursor.description]
        
        if rows:
            # Insert into target
            target_cursor = target_conn.cursor()
            placeholders = ','.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            
            target_cursor.executemany(insert_query, rows)
            target_conn.commit()
            
            print(f"Migrated {len(rows)} rows from {table}")
        
        source_cursor.close()
    
    source_conn.close()
    target_conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_supabase_to_rds()
```

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   ```sql
   -- Check active connections
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   
   -- Kill idle connections
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle' AND query_start < now() - interval '1 hour';
   ```

2. **PostGIS Not Working**
   ```sql
   -- Verify PostGIS installation
   SELECT name, default_version, installed_version 
   FROM pg_available_extensions 
   WHERE name LIKE 'postgis%';
   
   -- Check PostGIS functions
   SELECT proname FROM pg_proc WHERE proname LIKE 'st_%' LIMIT 10;
   ```

3. **Performance Issues**
   ```sql
   -- Check slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   
   -- Check index usage
   SELECT schemaname, tablename, indexname, idx_scan 
   FROM pg_stat_user_indexes 
   ORDER BY idx_scan ASC;
   ```

## Performance Optimization

### Query Optimization

```sql
-- Optimize spatial queries
SET enable_seqscan = OFF;  -- Force index usage for spatial queries

-- Example optimized query
EXPLAIN (ANALYZE, BUFFERS) 
SELECT p.name, ST_Area(p.study_area) 
FROM projects p 
WHERE ST_Contains(p.study_area, ST_Point(-47.7, -21.6));

-- Create specialized indexes
CREATE INDEX idx_projects_contains_point ON projects 
USING GIST (study_area) 
WHERE study_area IS NOT NULL;
```

### Connection Pool Tuning

```sql
-- Check connection pool efficiency
SELECT 
  application_name,
  count(*) as connections,
  state
FROM pg_stat_activity 
GROUP BY application_name, state
ORDER BY connections DESC;

-- Optimize PostgreSQL settings for spatial workloads
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET work_mem = '8MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';

-- Reload configuration
SELECT pg_reload_conf();
```

## Cost Optimization

### RDS Cost Analysis

| Instance Type | Monthly Cost (São Paulo) | Use Case |
|---------------|-------------------------|----------|
| db.t3.micro | ~$20 | Development/Testing |
| db.t3.small | ~$40 | Small production |
| db.t3.medium | ~$80 | Recommended production |
| db.t3.large | ~$160 | High-traffic production |

### Storage Costs

- **GP2 SSD**: $0.138/GB-month
- **Provisioned IOPS**: $0.138/GB-month + $0.138/IOPS-month
- **Backup Storage**: Free up to database size, then $0.110/GB-month

### Cost Optimization Tips

1. **Right-size instances** based on actual usage
2. **Use Reserved Instances** for 1-3 year commitments (up to 60% savings)
3. **Enable storage autoscaling** to avoid over-provisioning
4. **Monitor unused indexes** and remove them
5. **Implement data archiving** for old analysis results

---

This completes the AWS RDS PostgreSQL + PostGIS setup guide for production deployment in Brazil. The configuration ensures optimal performance, security, and compliance for the Wildfire Assessment Platform.