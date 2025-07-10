# Supabase Setup Guide (Development Environment)

## Overview

This guide walks through setting up Supabase as the development database for the Wildfire Assessment Platform. Supabase provides PostgreSQL with PostGIS, built-in authentication, and a web admin interface.

## Prerequisites

- Supabase account (free tier available)
- Node.js 16+ for local development
- Python 3.8+ for backend integration

## Step 1: Create Supabase Project

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click "New Project"
3. Choose organization and enter project details:
   - **Name**: `wildfire-assessment-dev`
   - **Database Password**: Generate a strong password
   - **Region**: Choose closest to team (or São Paulo if available)

## Step 2: Enable PostGIS Extension

```sql
-- Run in Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

## Step 3: Create Database Schema

### Core Tables

```sql
-- Enable Row Level Security
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

-- Organizations/Teams table
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  study_area GEOMETRY(Polygon, 4326),
  area_name TEXT, -- e.g., "luiz-antonio", "amazon", "cerrado"
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'processing')),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES auth.users(id),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Satellite images metadata
CREATE TABLE satellite_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  capture_date DATE NOT NULL,
  image_type TEXT NOT NULL CHECK (image_type IN ('rgb', 'ndvi', 'nbr', 'composite', 'severity')),
  s3_bucket TEXT NOT NULL,
  s3_key TEXT NOT NULL,
  file_size_bytes BIGINT,
  processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
  quality_score DECIMAL(3,2), -- 0-1 quality assessment
  cloud_coverage DECIMAL(5,2), -- percentage
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Analysis results
CREATE TABLE analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  analysis_type TEXT NOT NULL CHECK (analysis_type IN ('ndvi', 'nbr', 'burn_severity', 'temporal_comparison')),
  input_images UUID[] NOT NULL, -- Array of satellite_images.id
  result_data JSONB NOT NULL,
  processing_parameters JSONB DEFAULT '{}',
  output_files JSONB DEFAULT '{}', -- S3 paths for result files
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES auth.users(id)
);

-- User project permissions
CREATE TABLE user_project_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
  granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  granted_by UUID REFERENCES auth.users(id),
  UNIQUE(user_id, project_id)
);

-- Processing jobs queue
CREATE TABLE processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  job_type TEXT NOT NULL CHECK (job_type IN ('satellite_download', 'ndvi_calculation', 'nbr_calculation', 'burn_analysis')),
  status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
  parameters JSONB NOT NULL,
  result JSONB,
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by UUID REFERENCES auth.users(id)
);
```

### Indexes for Performance

```sql
-- Spatial indexes
CREATE INDEX idx_projects_study_area ON projects USING GIST (study_area);

-- Time-based indexes
CREATE INDEX idx_satellite_images_capture_date ON satellite_images (capture_date);
CREATE INDEX idx_analysis_results_created_at ON analysis_results (created_at);

-- Lookup indexes
CREATE INDEX idx_satellite_images_project_type ON satellite_images (project_id, image_type);
CREATE INDEX idx_analysis_results_project_type ON analysis_results (project_id, analysis_type);
CREATE INDEX idx_processing_jobs_status ON processing_jobs (status, created_at);
```

### Row Level Security (RLS) Policies

```sql
-- Projects: Users can only see projects they have permission for
CREATE POLICY "Users can view projects with permissions" ON projects
  FOR SELECT USING (
    id IN (
      SELECT project_id FROM user_project_permissions 
      WHERE user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update projects they have editor+ permissions" ON projects
  FOR UPDATE USING (
    id IN (
      SELECT project_id FROM user_project_permissions 
      WHERE user_id = auth.uid() AND role IN ('editor', 'admin')
    )
  );

-- Satellite images: Inherit from project permissions
CREATE POLICY "Users can view satellite images for their projects" ON satellite_images
  FOR SELECT USING (
    project_id IN (
      SELECT project_id FROM user_project_permissions 
      WHERE user_id = auth.uid()
    )
  );

-- Analysis results: Inherit from project permissions
CREATE POLICY "Users can view analysis results for their projects" ON analysis_results
  FOR SELECT USING (
    project_id IN (
      SELECT project_id FROM user_project_permissions 
      WHERE user_id = auth.uid()
    )
  );

-- Enable RLS on all tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE satellite_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_project_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;
```

## Step 4: Insert Sample Data

```sql
-- Insert sample organization
INSERT INTO organizations (id, name, description) VALUES 
('550e8400-e29b-41d4-a716-446655440000', 'Brazil FlyingLabs', 'Wildfire assessment and monitoring');

-- Insert sample project (Luiz Antônio area)
INSERT INTO projects (id, organization_id, name, description, area_name, study_area) VALUES 
(
  '550e8400-e29b-41d4-a716-446655440001',
  '550e8400-e29b-41d4-a716-446655440000',
  'Luiz Antônio Forest Monitoring',
  'NDVI and burn analysis for Luiz Antônio State Park',
  'luiz-antonio',
  ST_GeomFromText('POLYGON((-47.8 -21.5, -47.6 -21.5, -47.6 -21.7, -47.8 -21.7, -47.8 -21.5))', 4326)
);

-- Insert sample satellite image records
INSERT INTO satellite_images (project_id, capture_date, image_type, s3_bucket, s3_key, processing_status) VALUES 
(
  '550e8400-e29b-41d4-a716-446655440001',
  '2023-05-01',
  'rgb',
  'wildfire-assessment-images',
  'luiz-antonio/2023-05-01/rgb.tif',
  'completed'
),
(
  '550e8400-e29b-41d4-a716-446655440001',
  '2023-05-01',
  'ndvi',
  'wildfire-assessment-images',
  'luiz-antonio/2023-05-01/ndvi.tif',
  'completed'
);
```

## Step 5: Configure Environment Variables

Create `.env.local` file in your Next.js frontend:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Database URL for backend
DATABASE_URL=postgresql://postgres:your-password@db.your-project-ref.supabase.co:5432/postgres

# Application URLs
NEXT_PUBLIC_API_BASE=http://localhost:3000/api
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
```

## Step 6: Backend Integration (Python)

### Install Dependencies

```bash
pip install sqlalchemy geoalchemy2 psycopg2-binary python-dotenv
```

### Database Connection

```python
# database.py
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import Geometry
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=True  # Set to False in production
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Model Definitions

```python
# models.py
from sqlalchemy import Column, String, DateTime, Integer, Text, ARRAY, JSON, ForeignKey, Boolean, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from database import Base
import uuid
from datetime import datetime

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    name = Column(String, nullable=False)
    description = Column(Text)
    area_name = Column(String)
    study_area = Column(Geometry('POLYGON', srid=4326))
    status = Column(String, default='active')
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True))
    
    # Relationships
    satellite_images = relationship("SatelliteImage", back_populates="project")
    analysis_results = relationship("AnalysisResult", back_populates="project")

class SatelliteImage(Base):
    __tablename__ = "satellite_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    capture_date = Column(DateTime, nullable=False)
    image_type = Column(String, nullable=False)
    s3_bucket = Column(String, nullable=False)
    s3_key = Column(String, nullable=False)
    file_size_bytes = Column(Integer)
    processing_status = Column(String, default='pending')
    quality_score = Column(DECIMAL(3,2))
    cloud_coverage = Column(DECIMAL(5,2))
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="satellite_images")
```

## Step 7: Frontend Integration (Next.js)

### Install Supabase Client

```bash
npm install @supabase/supabase-js @supabase/auth-helpers-nextjs
```

### Supabase Client Setup

```typescript
// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'
import { Database } from './database.types'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey)
```

### Authentication Setup

```typescript
// pages/api/auth/[...nextauth].ts
import NextAuth from 'next-auth'
import { SupabaseAdapter } from '@next-auth/supabase-adapter'

export default NextAuth({
  providers: [
    // Add your authentication providers
  ],
  adapter: SupabaseAdapter({
    url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
    secret: process.env.SUPABASE_SERVICE_ROLE_KEY!,
  }),
})
```

### API Routes Example

```typescript
// pages/api/projects/index.ts
import { NextApiRequest, NextApiResponse } from 'next'
import { supabase } from '../../../lib/supabase'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    const { data: projects, error } = await supabase
      .from('projects')
      .select(`
        *,
        satellite_images(count),
        analysis_results(count)
      `)
      .order('created_at', { ascending: false })

    if (error) {
      return res.status(500).json({ error: error.message })
    }

    return res.status(200).json(projects)
  }

  if (req.method === 'POST') {
    const { name, description, study_area, area_name } = req.body

    const { data: project, error } = await supabase
      .from('projects')
      .insert({
        name,
        description,
        study_area,
        area_name,
        organization_id: '550e8400-e29b-41d4-a716-446655440000' // Default org
      })
      .select()
      .single()

    if (error) {
      return res.status(500).json({ error: error.message })
    }

    return res.status(201).json(project)
  }

  return res.status(405).json({ error: 'Method not allowed' })
}
```

## Step 8: Testing & Validation

### Test Spatial Queries

```sql
-- Test PostGIS functionality
SELECT 
  p.name,
  ST_Area(p.study_area) as area_sq_degrees,
  ST_AsText(ST_Centroid(p.study_area)) as centroid
FROM projects p;

-- Test data relationships
SELECT 
  p.name as project_name,
  COUNT(si.id) as image_count,
  COUNT(ar.id) as analysis_count
FROM projects p
LEFT JOIN satellite_images si ON p.id = si.project_id
LEFT JOIN analysis_results ar ON p.id = ar.project_id
GROUP BY p.id, p.name;
```

### Verify RLS Policies

```sql
-- Test row level security (should return only user's projects)
SELECT * FROM projects;
```

## Troubleshooting

### Common Issues

1. **PostGIS Extension Not Available**
   ```sql
   -- Check if PostGIS is installed
   SELECT * FROM pg_extension WHERE extname = 'postgis';
   
   -- If not found, contact Supabase support or use different region
   ```

2. **RLS Blocking Queries**
   ```sql
   -- Temporarily disable RLS for testing
   ALTER TABLE projects DISABLE ROW LEVEL SECURITY;
   
   -- Re-enable after fixing policies
   ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
   ```

3. **Connection Issues**
   - Verify environment variables are correct
   - Check Supabase project is active
   - Ensure IP address is whitelisted (if configured)

### Performance Optimization

```sql
-- Monitor query performance
EXPLAIN ANALYZE SELECT * FROM projects WHERE ST_Contains(study_area, ST_Point(-47.7, -21.6));

-- Add additional indexes if needed
CREATE INDEX idx_projects_area_gist ON projects USING GIST (study_area);
```

## Next Steps

1. **Migrate hardcoded data** from `valid-dates` API to database
2. **Implement user authentication** with Supabase Auth
3. **Connect analysis pipeline** to store results
4. **Set up automated backups** and monitoring

## Useful Commands

```bash
# Generate TypeScript types from Supabase schema
npx supabase gen types typescript --project-id your-project-ref > lib/database.types.ts

# Backup database
pg_dump "postgresql://postgres:password@db.project-ref.supabase.co:5432/postgres" > backup.sql

# Restore database
psql "postgresql://postgres:password@db.project-ref.supabase.co:5432/postgres" < backup.sql
```