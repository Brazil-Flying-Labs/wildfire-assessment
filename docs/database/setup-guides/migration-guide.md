# Database Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from the current hardcoded data structure to a proper database system. The migration supports both development (Supabase) and production (AWS RDS) environments.

## Migration Phases

### Phase 1: Development Database Setup (Week 1)
- Set up Supabase development database
- Create core schema
- Migrate hardcoded area data
- Implement basic authentication

### Phase 2: Application Integration (Week 2-3)
- Update API routes to use database
- Implement user management
- Connect analysis pipeline
- Test geospatial functionality

### Phase 3: Production Migration (Week 4-6)
- Set up AWS RDS in São Paulo
- Implement production security
- Data migration and testing
- Performance optimization

## Current Data Analysis

### Hardcoded Data to Migrate

**From:** `/src/app/api/valid-dates/route.ts`
```typescript
const VALID_DATES_BY_AREA: Record<string, string[]> = {
  'test-area4': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'luiz-antonio': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'jatai': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'sao-paulo': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'amazon': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'cerrado': ['2023-05-01', '2023-05-15', '2023-06-01'],
  'pantanal': ['2023-05-01', '2023-05-15', '2023-06-01']
};
```

**To:** Database tables with proper relationships and metadata

## Phase 1: Development Database Migration

### Step 1: Setup Supabase Database

1. Follow the [Supabase Setup Guide](./supabase-setup.md)
2. Create the core schema
3. Verify PostGIS functionality

### Step 2: Create Migration Scripts

Create migration scripts to populate initial data:

```sql
-- migrations/001_initial_data.sql

-- Insert default organization
INSERT INTO organizations (id, name, description) VALUES 
('550e8400-e29b-41d4-a716-446655440000', 'Brazil FlyingLabs', 'Wildfire assessment and environmental monitoring organization');

-- Insert study areas with proper geometry
INSERT INTO projects (id, organization_id, name, description, area_name, study_area) VALUES 
(
  '550e8400-e29b-41d4-a716-446655440001',
  '550e8400-e29b-41d4-a716-446655440000',
  'Luiz Antônio State Park',
  'Fire monitoring and assessment for Luiz Antônio State Park ecological station',
  'luiz-antonio',
  ST_GeomFromText('POLYGON((-47.8 -21.5, -47.6 -21.5, -47.6 -21.7, -47.8 -21.7, -47.8 -21.5))', 4326)
),
(
  '550e8400-e29b-41d4-a716-446655440002',
  '550e8400-e29b-41d4-a716-446655440000',
  'Jataí Ecological Station',
  'Environmental monitoring for Jataí Ecological Station',
  'jatai',
  ST_GeomFromText('POLYGON((-47.9 -21.6, -47.7 -21.6, -47.7 -21.8, -47.9 -21.8, -47.9 -21.6))', 4326)
),
(
  '550e8400-e29b-41d4-a716-446655440003',
  '550e8400-e29b-41d4-a716-446655440000',
  'São Paulo State Monitoring',
  'Statewide fire monitoring and prevention',
  'sao-paulo',
  ST_GeomFromText('POLYGON((-48.0 -22.0, -46.0 -22.0, -46.0 -24.0, -48.0 -24.0, -48.0 -22.0))', 4326)
),
(
  '550e8400-e29b-41d4-a716-446655440004',
  '550e8400-e29b-41d4-a716-446655440000',
  'Amazon Basin Study Area',
  'Large-scale fire monitoring in the Amazon basin',
  'amazon',
  ST_GeomFromText('POLYGON((-65.0 -5.0, -55.0 -5.0, -55.0 -15.0, -65.0 -15.0, -65.0 -5.0))', 4326)
),
(
  '550e8400-e29b-41d4-a716-446655440005',
  '550e8400-e29b-41d4-a716-446655440000',
  'Cerrado Biome Monitoring',
  'Fire assessment across the Cerrado savanna biome',
  'cerrado',
  ST_GeomFromText('POLYGON((-50.0 -10.0, -45.0 -10.0, -45.0 -20.0, -50.0 -20.0, -50.0 -10.0))', 4326)
),
(
  '550e8400-e29b-41d4-a716-446655440006',
  '550e8400-e29b-41d4-a716-446655440000',
  'Pantanal Wetlands',
  'Fire monitoring in the Pantanal wetland ecosystem',
  'pantanal',
  ST_GeomFromText('POLYGON((-58.0 -16.0, -55.0 -16.0, -55.0 -20.0, -58.0 -20.0, -58.0 -16.0))', 4326)
);

-- Insert satellite image metadata for available dates
INSERT INTO satellite_images (project_id, capture_date, image_type, s3_bucket, s3_key, processing_status) 
SELECT 
  p.id,
  date_val::date,
  'rgb',
  'wildfire-assessment-images',
  p.area_name || '/' || date_val || '/rgb.tif',
  'completed'
FROM projects p
CROSS JOIN (
  VALUES 
    ('2023-05-01'),
    ('2023-05-15'),
    ('2023-06-01')
) AS dates(date_val)
WHERE p.area_name IS NOT NULL;

-- Insert corresponding NDVI and NBR images
INSERT INTO satellite_images (project_id, capture_date, image_type, s3_bucket, s3_key, processing_status)
SELECT 
  project_id,
  capture_date,
  image_type,
  s3_bucket,
  REPLACE(s3_key, '/rgb.tif', '/' || image_type || '.tif'),
  processing_status
FROM satellite_images si
CROSS JOIN (VALUES ('ndvi'), ('nbr')) AS types(image_type)
WHERE si.image_type = 'rgb';
```

### Step 3: Update API Routes

Update the existing API routes to use the database:

```typescript
// src/app/api/valid-dates/route.ts (updated)
import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const areaId = searchParams.get('areaId');

    if (!areaId) {
      return NextResponse.json(
        { error: 'areaId parameter is required' },
        { status: 400 }
      );
    }

    // Query database for available dates
    const { data: images, error } = await supabase
      .from('satellite_images')
      .select('capture_date, projects!inner(area_name)')
      .eq('projects.area_name', areaId)
      .eq('processing_status', 'completed')
      .order('capture_date', { ascending: true });

    if (error) {
      console.error('Database error:', error);
      return NextResponse.json(
        { error: 'Failed to fetch valid dates from database' },
        { status: 500 }
      );
    }

    // Extract unique dates
    const validDates = [...new Set(images?.map(img => img.capture_date) || [])];

    return NextResponse.json({ validDates });
  } catch (error) {
    console.error('Error in valid-dates API route:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

### Step 4: Create New API Endpoints

Create comprehensive API endpoints for the new data structure:

```typescript
// src/app/api/projects/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET() {
  try {
    const { data: projects, error } = await supabase
      .from('projects')
      .select(`
        *,
        organizations(name),
        satellite_images(count),
        analysis_results(count)
      `)
      .eq('status', 'active')
      .order('created_at', { ascending: false });

    if (error) throw error;

    return NextResponse.json(projects);
  } catch (error) {
    console.error('Error fetching projects:', error);
    return NextResponse.json(
      { error: 'Failed to fetch projects' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, description, area_name, study_area } = body;

    const { data: project, error } = await supabase
      .from('projects')
      .insert({
        name,
        description,
        area_name,
        study_area,
        organization_id: '550e8400-e29b-41d4-a716-446655440000' // Default org
      })
      .select()
      .single();

    if (error) throw error;

    return NextResponse.json(project, { status: 201 });
  } catch (error) {
    console.error('Error creating project:', error);
    return NextResponse.json(
      { error: 'Failed to create project' },
      { status: 500 }
    );
  }
}
```

```typescript
// src/app/api/projects/[id]/images/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { searchParams } = new URL(request.url);
    const imageType = searchParams.get('type');
    const startDate = searchParams.get('start_date');
    const endDate = searchParams.get('end_date');

    let query = supabase
      .from('satellite_images')
      .select('*')
      .eq('project_id', params.id)
      .eq('processing_status', 'completed')
      .order('capture_date', { ascending: false });

    if (imageType) {
      query = query.eq('image_type', imageType);
    }

    if (startDate) {
      query = query.gte('capture_date', startDate);
    }

    if (endDate) {
      query = query.lte('capture_date', endDate);
    }

    const { data: images, error } = await query;

    if (error) throw error;

    return NextResponse.json(images);
  } catch (error) {
    console.error('Error fetching project images:', error);
    return NextResponse.json(
      { error: 'Failed to fetch project images' },
      { status: 500 }
    );
  }
}
```

## Phase 2: Application Integration

### Step 1: Update Frontend Components

Update React components to use the new database structure:

```typescript
// src/components/project-selector.tsx
'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

interface Project {
  id: string;
  name: string;
  area_name: string;
  description: string;
}

export function ProjectSelector({ onProjectSelect }: { 
  onProjectSelect: (project: Project) => void 
}) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProjects() {
      try {
        const { data, error } = await supabase
          .from('projects')
          .select('id, name, area_name, description')
          .eq('status', 'active')
          .order('name');

        if (error) throw error;
        setProjects(data || []);
      } catch (error) {
        console.error('Error fetching projects:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchProjects();
  }, []);

  if (loading) {
    return <div>Loading projects...</div>;
  }

  return (
    <select onChange={(e) => {
      const project = projects.find(p => p.id === e.target.value);
      if (project) onProjectSelect(project);
    }}>
      <option value="">Select a project</option>
      {projects.map(project => (
        <option key={project.id} value={project.id}>
          {project.name}
        </option>
      ))}
    </select>
  );
}
```

### Step 2: Implement Authentication

Set up user authentication and project permissions:

```typescript
// src/lib/auth.ts
import { supabase } from './supabase';

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) throw error;
  return data;
}

export async function signUp(email: string, password: string, fullName: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
      },
    },
  });

  if (error) throw error;

  // Create user profile
  if (data.user) {
    const { error: profileError } = await supabase
      .from('app_users')
      .insert({
        id: data.user.id,
        email: data.user.email,
        full_name: fullName,
        organization_id: '550e8400-e29b-41d4-a716-446655440000' // Default org
      });

    if (profileError) throw profileError;
  }

  return data;
}

export async function getCurrentUser() {
  const { data: { user } } = await supabase.auth.getUser();
  
  if (!user) return null;

  const { data: profile, error } = await supabase
    .from('app_users')
    .select('*')
    .eq('id', user.id)
    .single();

  if (error) throw error;

  return { ...user, profile };
}

export async function getUserProjects(userId: string) {
  const { data, error } = await supabase
    .from('user_project_permissions')
    .select(`
      role,
      projects (
        id,
        name,
        description,
        area_name,
        status
      )
    `)
    .eq('user_id', userId);

  if (error) throw error;
  return data;
}
```

### Step 3: Update Analysis Pipeline

Modify the analysis pipeline to store results in the database:

```python
# backend/analysis/pipeline.py
import uuid
import json
from datetime import datetime
from database import get_db
from models import AnalysisResult, ProcessingJob

class WildfireAnalysisPipeline:
    def __init__(self, project_id: str, analysis_type: str, user_id: str):
        self.project_id = project_id
        self.analysis_type = analysis_type
        self.user_id = user_id
        self.db = next(get_db())

    def create_job(self, parameters: dict) -> str:
        """Create a processing job record"""
        job = ProcessingJob(
            project_id=self.project_id,
            job_type=self.analysis_type,
            parameters=parameters,
            created_by=self.user_id
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        return str(job.id)

    def update_job_status(self, job_id: str, status: str, result: dict = None, error: str = None):
        """Update job status and results"""
        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = status
            if result:
                job.result = result
            if error:
                job.error_message = error
            if status in ['completed', 'failed']:
                job.completed_at = datetime.utcnow()
            
            self.db.commit()

    def store_analysis_result(self, job_id: str, result_data: dict, input_images: list, 
                            output_files: dict = None) -> str:
        """Store analysis results in database"""
        
        # Calculate statistics from result
        total_area = result_data.get('total_area_hectares', 0)
        burned_area = result_data.get('burned_area_hectares', 0)
        severity_dist = result_data.get('severity_distribution', {})
        
        analysis_result = AnalysisResult(
            project_id=self.project_id,
            analysis_type=self.analysis_type,
            input_images=input_images,
            result_data=result_data,
            output_files=output_files or {},
            total_area_hectares=total_area,
            burned_area_hectares=burned_area,
            severity_distribution=severity_dist,
            created_by=self.user_id
        )
        
        self.db.add(analysis_result)
        self.db.commit()
        self.db.refresh(analysis_result)
        
        return str(analysis_result.id)

    def run_ndvi_analysis(self, input_date: str, parameters: dict):
        """Run NDVI analysis and store results"""
        job_id = self.create_job({
            'analysis_type': 'ndvi',
            'input_date': input_date,
            **parameters
        })
        
        try:
            self.update_job_status(job_id, 'running')
            
            # Get input images
            input_images = self.get_input_images_for_date(input_date, 'rgb')
            
            # Run analysis (existing Google Earth Engine code)
            result = self.calculate_ndvi(input_images, parameters)
            
            # Store results
            analysis_id = self.store_analysis_result(
                job_id=job_id,
                result_data=result,
                input_images=[str(img.id) for img in input_images]
            )
            
            self.update_job_status(job_id, 'completed', {'analysis_id': analysis_id})
            
            return analysis_id
            
        except Exception as e:
            self.update_job_status(job_id, 'failed', error=str(e))
            raise

    def get_input_images_for_date(self, date: str, image_type: str):
        """Get satellite images for analysis"""
        from models import SatelliteImage
        
        return self.db.query(SatelliteImage).filter(
            SatelliteImage.project_id == self.project_id,
            SatelliteImage.capture_date == date,
            SatelliteImage.image_type == image_type,
            SatelliteImage.processing_status == 'completed'
        ).all()
```

## Phase 3: Production Migration

### Step 1: AWS RDS Setup

Follow the [AWS RDS Setup Guide](./aws-rds-setup.md) to:
1. Deploy VPC and security groups
2. Create RDS PostgreSQL instance with PostGIS
3. Set up monitoring and backups
4. Configure connection pooling

### Step 2: Environment Configuration

Update environment variables for production:

```env
# Production environment variables
NODE_ENV=production

# Database (AWS RDS)
DATABASE_URL=postgresql://app_user:password@wildfire-prod.amazonaws.com:5432/wildfire_assessment
DB_HOST=wildfire-prod.amazonaws.com
DB_PORT=5432
DB_NAME=wildfire_assessment
DB_USER=app_user
DB_SSL_MODE=require

# AWS Configuration
AWS_REGION=sa-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# S3 Storage
S3_BUCKET_IMAGES=wildfire-images-prod
S3_BUCKET_EXPORTS=wildfire-exports-prod

# Application URLs
NEXT_PUBLIC_API_BASE=https://api.wildfire-assessment.com
NEXTAUTH_URL=https://wildfire-assessment.com

# Monitoring
SENTRY_DSN=https://...
LOG_LEVEL=info

# Authentication
JWT_SECRET=production_jwt_secret
NEXTAUTH_SECRET=production_nextauth_secret
```

### Step 3: Data Migration

Create and run production data migration:

```python
# scripts/migrate_to_production.py
import os
import logging
import psycopg2
import psycopg2.extras
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_development_to_production():
    """Migrate data from Supabase development to AWS RDS production"""
    
    # Source (Supabase development)
    source_config = {
        'host': os.getenv('SUPABASE_HOST'),
        'database': os.getenv('SUPABASE_DATABASE'),
        'user': os.getenv('SUPABASE_USER'),
        'password': os.getenv('SUPABASE_PASSWORD'),
        'port': 5432
    }
    
    # Target (AWS RDS production)
    target_config = {
        'host': os.getenv('RDS_HOST'),
        'database': os.getenv('RDS_DATABASE'),
        'user': os.getenv('RDS_USER'),
        'password': os.getenv('RDS_PASSWORD'),
        'port': 5432,
        'sslmode': 'require'
    }
    
    # Tables to migrate in order (respecting foreign key constraints)
    migration_order = [
        'organizations',
        'app_users',
        'projects',
        'satellite_images',
        'analysis_results',
        'user_project_permissions',
        'processing_jobs',
        'data_exports'
    ]
    
    try:
        # Connect to both databases
        source_conn = psycopg2.connect(**source_config)
        target_conn = psycopg2.connect(**target_config)
        
        source_conn.set_session(readonly=True)
        
        for table in migration_order:
            logger.info(f"Migrating table: {table}")
            
            # Check if table exists in source
            source_cursor = source_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            source_cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """, (table,))
            
            columns_info = source_cursor.fetchall()
            if not columns_info:
                logger.warning(f"Table {table} not found in source database")
                continue
            
            columns = [col['column_name'] for col in columns_info]
            
            # Extract data from source
            source_cursor.execute(f"SELECT * FROM {table}")
            rows = source_cursor.fetchall()
            
            if not rows:
                logger.info(f"No data found in {table}")
                continue
            
            # Prepare target insertion
            target_cursor = target_conn.cursor()
            
            # Clear existing data in target (be careful in production!)
            if os.getenv('MIGRATION_MODE') == 'clean':
                target_cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                logger.info(f"Cleared existing data in {table}")
            
            # Insert data into target
            placeholders = ','.join(['%s'] * len(columns))
            insert_query = f"""
                INSERT INTO {table} ({','.join(columns)}) 
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            # Convert rows to tuples for insertion
            data_tuples = []
            for row in rows:
                tuple_data = []
                for col in columns:
                    value = row[col]
                    # Handle JSON columns
                    if isinstance(value, dict) or isinstance(value, list):
                        value = json.dumps(value)
                    tuple_data.append(value)
                data_tuples.append(tuple(tuple_data))
            
            target_cursor.executemany(insert_query, data_tuples)
            target_conn.commit()
            
            logger.info(f"Migrated {len(rows)} rows to {table}")
            
            source_cursor.close()
            target_cursor.close()
        
        # Verify migration
        verify_migration(source_conn, target_conn, migration_order)
        
        source_conn.close()
        target_conn.close()
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

def verify_migration(source_conn, target_conn, tables):
    """Verify that migration was successful"""
    logger.info("Verifying migration...")
    
    for table in tables:
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()
        
        source_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        source_count = source_cursor.fetchone()[0]
        
        target_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        target_count = target_cursor.fetchone()[0]
        
        if source_count == target_count:
            logger.info(f"✓ {table}: {source_count} rows matched")
        else:
            logger.error(f"✗ {table}: source={source_count}, target={target_count}")
        
        source_cursor.close()
        target_cursor.close()

if __name__ == "__main__":
    migrate_development_to_production()
```

### Step 4: Performance Testing

Run performance tests to ensure the production database can handle the expected load:

```python
# scripts/performance_test.py
import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import psycopg2

async def test_api_performance():
    """Test API endpoint performance"""
    base_url = "https://api.wildfire-assessment.com"
    
    endpoints = [
        "/api/projects",
        "/api/projects/550e8400-e29b-41d4-a716-446655440001/images",
        "/api/valid-dates?areaId=luiz-antonio",
    ]
    
    results = {}
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            response_times = []
            
            # Run 50 requests per endpoint
            for i in range(50):
                start_time = time.time()
                
                async with session.get(f"{base_url}{endpoint}") as response:
                    await response.text()
                    
                response_time = time.time() - start_time
                response_times.append(response_time)
            
            results[endpoint] = {
                'mean': statistics.mean(response_times),
                'median': statistics.median(response_times),
                'p95': sorted(response_times)[int(0.95 * len(response_times))],
                'max': max(response_times)
            }
    
    # Print results
    print("API Performance Test Results:")
    for endpoint, metrics in results.items():
        print(f"\n{endpoint}:")
        print(f"  Mean: {metrics['mean']:.3f}s")
        print(f"  Median: {metrics['median']:.3f}s")
        print(f"  95th percentile: {metrics['p95']:.3f}s")
        print(f"  Max: {metrics['max']:.3f}s")

def test_database_performance():
    """Test database query performance"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    queries = [
        ("Simple select", "SELECT COUNT(*) FROM projects"),
        ("Spatial query", """
            SELECT name, ST_Area(study_area) 
            FROM projects 
            WHERE ST_Contains(study_area, ST_Point(-47.7, -21.6))
        """),
        ("Complex join", """
            SELECT p.name, COUNT(si.id) as image_count, COUNT(ar.id) as analysis_count
            FROM projects p
            LEFT JOIN satellite_images si ON p.id = si.project_id
            LEFT JOIN analysis_results ar ON p.id = ar.project_id
            GROUP BY p.id, p.name
        """),
    ]
    
    cursor = conn.cursor()
    
    print("\nDatabase Performance Test Results:")
    for query_name, query in queries:
        times = []
        
        for i in range(10):
            start_time = time.time()
            cursor.execute(query)
            cursor.fetchall()
            query_time = time.time() - start_time
            times.append(query_time)
        
        print(f"\n{query_name}:")
        print(f"  Mean: {statistics.mean(times):.3f}s")
        print(f"  Max: {max(times):.3f}s")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    asyncio.run(test_api_performance())
    test_database_performance()
```

## Migration Checklist

### Pre-Migration
- [ ] Set up development database (Supabase)
- [ ] Create and test database schema
- [ ] Implement core API endpoints
- [ ] Test authentication system
- [ ] Verify geospatial functionality

### Development Migration
- [ ] Run initial data migration scripts
- [ ] Update API routes to use database
- [ ] Test frontend components with new APIs
- [ ] Implement user authentication
- [ ] Verify data integrity

### Production Preparation  
- [ ] Set up AWS RDS in São Paulo region
- [ ] Configure VPC and security groups
- [ ] Set up monitoring and alerts
- [ ] Create backup and recovery procedures
- [ ] Performance test with expected load

### Production Migration
- [ ] Run production data migration
- [ ] Update application configuration
- [ ] Test all functionality in production
- [ ] Monitor performance and errors
- [ ] Verify data integrity and completeness

### Post-Migration
- [ ] Remove hardcoded data from codebase
- [ ] Update documentation
- [ ] Train team on new database system
- [ ] Set up ongoing maintenance procedures
- [ ] Monitor performance and optimize as needed

## Rollback Procedures

### Development Rollback
If issues occur during development migration:

1. **Revert API Routes**
   ```bash
   git checkout main -- src/app/api/
   npm run build
   npm run dev
   ```

2. **Restore Hardcoded Data**
   - Keep backup of original `valid-dates/route.ts`
   - Quickly switch back if needed

### Production Rollback
If critical issues occur during production migration:

1. **Database Rollback**
   ```bash
   # Restore from backup
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier wildfire-assessment-prod-rollback \
     --db-snapshot-identifier wildfire-assessment-backup-YYYYMMDD
   ```

2. **Application Rollback**
   ```bash
   # Deploy previous version
   git revert HEAD
   npm run build
   # Deploy to production
   ```

3. **DNS Switch**
   ```bash
   # Point traffic back to old system if necessary
   aws route53 change-resource-record-sets \
     --hosted-zone-id Z123456789 \
     --change-batch file://rollback-dns.json
   ```

## Troubleshooting

### Common Migration Issues

1. **Data Type Mismatches**
   ```sql
   -- Check data types
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'problematic_table';
   
   -- Fix UUID vs text issues
   ALTER TABLE table_name ALTER COLUMN id TYPE UUID USING id::UUID;
   ```

2. **Foreign Key Violations**
   ```sql
   -- Check orphaned records
   SELECT t1.id FROM table1 t1 
   LEFT JOIN table2 t2 ON t1.foreign_key = t2.id 
   WHERE t2.id IS NULL;
   
   -- Clean up orphaned records
   DELETE FROM table1 WHERE foreign_key NOT IN (SELECT id FROM table2);
   ```

3. **PostGIS Installation Issues**
   ```sql
   -- Verify PostGIS is properly installed
   SELECT PostGIS_version();
   
   -- If not available, install extensions
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS postgis_topology;
   ```

4. **Performance Issues**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_table_column ON table_name (column_name);
   
   -- Analyze tables after migration
   ANALYZE;
   
   -- Update table statistics
   VACUUM ANALYZE;
   ```

### Monitoring Migration Health

```sql
-- Check migration progress
SELECT 
  schemaname,
  tablename,
  n_tup_ins as inserts,
  n_tup_upd as updates,
  n_tup_del as deletes,
  last_analyze,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;

-- Monitor active connections during migration
SELECT 
  state,
  count(*) as connections
FROM pg_stat_activity 
GROUP BY state;

-- Check for blocking queries
SELECT 
  blocked_locks.pid AS blocked_pid,
  blocked_activity.usename AS blocked_user,
  blocking_locks.pid AS blocking_pid,
  blocking_activity.usename AS blocking_user,
  blocked_activity.query AS blocked_statement,
  blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

This migration guide provides a comprehensive roadmap for transitioning from hardcoded data to a proper database system, supporting both development and production environments while ensuring data integrity and system reliability.