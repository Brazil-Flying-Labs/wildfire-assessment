# Lambda Container Migration - Part 2

Date: 2025-05-20

## Summary

Successfully migrated all Lambda functions (RGB, NDVI, NBR, and diff) to container-based deployments using Docker images. This approach eliminates the need for Lambda layers and simplifies dependency management, particularly for complex libraries like rasterio and rio-tiler.

## Tasks Completed

- [x] Fixed Docker build issues by using pre-built wheels for rasterio and rio-tiler
- [x] Identified the key issue: building for x86_64 architecture is required for pre-built wheels
- [x] Simplified Dockerfiles to use minimal approach with pre-built wheels
- [x] Updated requirements.txt files to use specific versions that have pre-built wheels
- [x] Added platform flag to Dockerfiles to ensure they build for x86_64 architecture
- [x] Updated CDK stack to include build args for Docker images
- [x] Successfully built and deployed all Lambda functions as container images

## Technical Details

The key insight was understanding that rasterio and rio-tiler have pre-built wheels available for x86_64 architecture, but not for ARM. Since we're building on an M-series Mac (ARM architecture), we needed to explicitly specify the target platform as linux/amd64 to use these pre-built wheels.

### Final Dockerfile Structure

```dockerfile
# Build for x86_64 architecture to use pre-built wheels
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.10

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy handler code
COPY handler.py .

# Lambda entry point
CMD ["handler.main"]
```

### Dependencies

We pinned specific versions of dependencies that have pre-built wheels available:

```
rio-tiler==5.0.3
rasterio==1.3.8
numexpr==2.8.1
numpy
pillow
boto3
requests
```

## Research Notes

After extensive research and experimentation, we found that:

1. Rasterio wheels since version 1.3.0 include GDAL bundled inside the wheel
2. Building for x86_64 allows us to use pre-built wheels, avoiding compilation issues
3. The AWS Lambda Python runtime is compatible with these pre-built wheels

## Next Steps

- [ ] Monitor the deployed Lambda functions for performance and cold start times
- [ ] Consider adding CloudWatch alarms for Lambda function errors
- [ ] Update documentation to reflect the new container-based deployment approach
