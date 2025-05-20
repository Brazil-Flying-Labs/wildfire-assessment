# BFL Backend Implementation

## Project Overview
Building a serverless backend for satellite imagery processing with the following components:
- EventBridge triggers for scheduled processing
- Step Functions for orchestration
- Lambda functions for STAC queries and image processing
- S3 bucket for public image storage
- Support for RGB, NDVI, NBR, and difference calculations

## Implementation Checklist
- [x] Set up project structure
- [x] Create CDK infrastructure
  - [x] S3 bucket configuration
  - [x] Lambda Layer with GDAL + rio-tiler
  - [x] Query Lambda function
  - [x] RGB/NDVI/NBR Lambda functions
  - [x] Step Functions workflow
  - [x] EventBridge rules
  - [x] Diff Lambda function with Function URL
- [x] Implement Lambda handlers
  - [x] Query handler
  - [x] RGB handler
  - [x] NDVI handler
  - [x] NBR handler
  - [x] Diff handler
- [x] Create deployment resources
  - [x] Lambda layer Dockerfile and build script
  - [x] Detailed deployment guide
  - [x] Helper scripts for area management
  - [x] Test event for Step Functions

## Progress Log

### 2025-05-20
- Started implementation of BFL backend based on provided specifications
- Created project structure and initialized CDK project
- Implemented CDK infrastructure stack with the following components:
  - Public S3 bucket for storing processed imagery
  - Lambda Layer configuration for GDAL + rio-tiler
  - Query Lambda for discovering least cloudy Sentinel-2 scenes
  - RGB/NDVI/NBR Lambda functions for processing imagery
  - Step Functions workflow for orchestration
  - EventBridge rules for scheduling processing
  - Diff Lambda with Function URL for on-demand difference calculations
- Implemented all Lambda handlers:
  - Query handler for STAC API integration
  - RGB handler for generating RGB composite images
  - NDVI handler for calculating vegetation index
  - NBR handler for calculating burn ratio
  - Diff handler for calculating differences between dates
- Created documentation for the Lambda layer and project README
- Added Docker setup for building the Lambda layer with GDAL and rio-tiler
- Created detailed deployment guide (DEPLOYMENT.md) with step-by-step instructions
- Implemented helper scripts for area management and manual processing:
  - `scripts/add-area.js`: Script to add new areas to the DynamoDB table
  - `scripts/trigger-processing.js`: Script to manually trigger processing for a specific area and date
- Fixed CDK stack lint errors and improved the EventBridge trigger mechanism
