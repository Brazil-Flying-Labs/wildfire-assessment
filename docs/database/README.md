# Database Architecture & Setup Guide

## Executive Summary

This document provides database recommendations for the Wildfire Assessment Platform, considering the Brazilian team context (Brazil FlyingLabs), geospatial data requirements, and integration with Fundação Florestal.

**Quick Recommendation:** AWS RDS PostgreSQL + PostGIS in São Paulo region for production, with Supabase for rapid prototyping.

## Current System Analysis

### Existing Data Sources
- **Amazon S3**: Satellite imagery (GeoTIFF files)
- **Google Earth Engine**: Geospatial processing and analysis
- **Static Files**: Hardcoded area configurations and date ranges

### Missing Database Layer
The current system lacks persistent storage for:
- User accounts and authentication
- Project and area metadata  
- Analysis results and processing history
- Geospatial boundary definitions
- File metadata and relationships

## Database Requirements

### Core Data Entities
1. **Users & Authentication**
   - User accounts for researchers, administrators
   - Project permissions and access control
   - Session management

2. **Projects & Areas**
   - Study area definitions (polygons)
   - Project metadata and configurations
   - Geographic boundaries for analysis

3. **Satellite Data Metadata**
   - Image capture dates and sources
   - Processing status and quality metrics
   - File paths and S3 locations

4. **Analysis Results**
   - NDVI/NBR calculation results
   - Burn severity classifications
   - Temporal comparison outputs
   - Processing logs and parameters

5. **Geospatial Data**
   - Polygon boundaries for study areas
   - Point locations (monitoring stations)
   - Coordinate reference systems
   - Spatial queries and relationships

## Recommended Database Options

### Option 1: AWS RDS PostgreSQL + PostGIS (Recommended for Production)

**Best For:** Production deployment with Brazilian compliance requirements

#### Advantages
- ✅ **Geospatial Excellence**: PostGIS is the industry standard for spatial data
- ✅ **Brazil Hosting**: São Paulo region ensures low latency and data residency
- ✅ **AWS Integration**: Seamless integration with existing S3 and Lambda infrastructure
- ✅ **Scalability**: Handles growing data volumes and user base
- ✅ **Python Support**: Excellent SQLAlchemy and GeoAlchemy2 integration

#### Considerations
- ⚠️ **Setup Complexity**: Requires some database administration knowledge
- ⚠️ **No Built-in Auth**: Must implement user authentication separately
- ⚠️ **Additional AWS Services**: Need Cognito or custom auth solution

#### Cost Estimate
- RDS db.t3.medium: ~$70-100/month
- Storage (500GB): ~$50/month
- **Total**: ~$120-150/month

### Option 2: Supabase (Recommended for Development)

**Best For:** Rapid prototyping and development phase

#### Advantages
- ✅ **Rapid Setup**: Database, auth, and admin UI in minutes
- ✅ **PostGIS Support**: Full geospatial capabilities
- ✅ **Built-in Features**: Authentication, file storage, real-time subscriptions
- ✅ **Developer Experience**: Excellent documentation and tooling
- ✅ **REST API**: Auto-generated APIs for all tables

#### Considerations
- ⚠️ **Non-Brazil Hosting**: Primary infrastructure outside Brazil
- ⚠️ **Compliance Risk**: May not meet strict data residency requirements
- ⚠️ **Vendor Lock-in**: Less control over infrastructure

#### Cost Estimate
- Pro Plan: $25/month (includes auth, storage, bandwidth)
- **Total**: ~$25-50/month

### Option 3: Google Cloud SQL PostgreSQL

**Best For:** Teams already invested in Google Earth Engine

#### Advantages
- ✅ **GEE Integration**: Natural fit with existing Google Earth Engine usage
- ✅ **São Paulo Hosting**: Brazilian data residency
- ✅ **PostGIS Support**: Full geospatial capabilities
- ✅ **Managed Service**: Automated backups, updates, monitoring

#### Considerations
- ⚠️ **Learning Curve**: Additional Google Cloud platform knowledge required
- ⚠️ **Custom Auth**: Must build authentication system

## Implementation Recommendations

### Phase 1: Development (Immediate)
**Use Supabase for rapid development:**

```sql
-- Core tables structure
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  study_area GEOMETRY(Polygon, 4326),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES auth.users(id)
);

CREATE TABLE satellite_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  capture_date DATE NOT NULL,
  s3_path TEXT NOT NULL,
  image_type TEXT CHECK (image_type IN ('rgb', 'ndvi', 'nbr', 'composite')),
  processing_status TEXT DEFAULT 'pending',
  metadata JSONB
);

CREATE TABLE analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  analysis_type TEXT NOT NULL,
  input_images UUID[] REFERENCES satellite_images(id),
  result_data JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Phase 2: Production Migration
**Migrate to AWS RDS PostgreSQL + PostGIS:**

1. **Database Setup**
   ```yaml
   # CDK configuration
   engine: postgres13
   instance_class: db.t3.medium
   allocated_storage: 500
   storage_encrypted: true
   multi_az: true
   vpc_security_groups: [database-sg]
   availability_zone: us-east-1a
   ```

2. **Authentication Integration**
   - AWS Cognito for user management
   - JWT tokens for API authentication
   - Role-based access control

3. **Data Migration**
   - Export from Supabase using pg_dump
   - Import to RDS using standard PostgreSQL tools
   - Update application connection strings

## Environment Variables & Configuration

### Required Environment Variables

```env
# Database Connection
DATABASE_URL=postgresql://username:password@host:port/database
DB_HOST=your-rds-endpoint.amazonaws.com
DB_PORT=5432
DB_NAME=wildfire_assessment
DB_USER=app_user
DB_PASSWORD=secure_password

# AWS Configuration (for RDS option)
AWS_REGION=sa-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Supabase Configuration (for development)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Application Settings
NEXT_PUBLIC_API_BASE=https://your-api-domain.com
NEXTAUTH_SECRET=your_auth_secret
NEXTAUTH_URL=https://your-app-domain.com
```

### Security Configuration

```python
# Python backend database configuration
import os
from sqlalchemy import create_engine
from geoalchemy2 import Geometry

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set to True for development
)

# Connection pooling for production
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 120,
    'pool_pre_ping': True,
    'max_overflow': 20
}
```

## Security & Compliance

### Data Protection
- **Encryption at Rest**: Enable for all database storage
- **Encryption in Transit**: SSL/TLS for all database connections
- **Access Control**: VPC security groups and IAM roles
- **Backup Strategy**: Automated daily backups with point-in-time recovery

### Brazilian Compliance
- **Data Residency**: Use São Paulo AWS region or Brazilian hosting
- **LGPD Compliance**: Implement data retention and deletion policies
- **Access Logs**: Enable CloudTrail and database audit logging

### Secure Client Sharing
```javascript
// Frontend API configuration with authentication
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE,
  headers: {
    'Authorization': `Bearer ${getAuthToken()}`,
    'Content-Type': 'application/json'
  }
});

// Row Level Security (RLS) policies in Supabase
CREATE POLICY "Users can only access their projects" ON projects
  FOR ALL USING (created_by = auth.uid());
```

## Next Steps

### Immediate Actions (Week 1)
1. Set up Supabase development database
2. Create core schema (projects, users, satellite_images)
3. Implement basic authentication
4. Test geospatial queries with PostGIS

### Short Term (Month 1)
1. Migrate hardcoded area data to database
2. Implement project and user management
3. Connect analysis pipeline to store results
4. Set up automated backups

### Production Preparation (Month 2-3)
1. Provision AWS RDS in São Paulo region
2. Set up AWS Cognito for authentication
3. Implement data migration scripts
4. Performance testing and optimization

## Cost Analysis

| Option | Setup Cost | Monthly Cost | Annual Cost |
|--------|------------|--------------|-------------|
| Supabase Pro | $0 | $25-50 | $300-600 |
| AWS RDS (t3.medium) | $200 | $120-150 | $1,440-1,800 |
| Google Cloud SQL | $200 | $100-130 | $1,200-1,560 |

## Support & Documentation

### Learning Resources
- [PostGIS Documentation](https://postgis.net/documentation/)
- [Supabase Docs](https://supabase.com/docs)
- [AWS RDS PostgreSQL Guide](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [SQLAlchemy GeoAlchemy2](https://geoalchemy-2.readthedocs.io/)

### Team Training Recommendations
1. **PostgreSQL Fundamentals** (2-3 days)
2. **PostGIS Spatial Queries** (1-2 days)
3. **Python ORM (SQLAlchemy)** (2-3 days)
4. **Database Administration Basics** (2-3 days)

---

**For questions or setup assistance, contact the infrastructure team or refer to the detailed setup guides in the following sections.**