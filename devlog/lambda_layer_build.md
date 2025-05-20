# Lambda Layer Strategy for BFL Backend

## Overview
We need a Lambda layer containing GDAL, rasterio, and rio-tiler for our satellite image processing functions. After exploring several options, we've decided to use a simpler approach.

## Attempted Approaches

### Approach 1: Using External Layer
- Tried to use a pre-built layer (`arn:aws:lambda:us-east-1:552819999234:layer:TiTilerLayer:1`)
- Encountered permission issues - our account doesn't have access to this layer

### Approach 2: Building Custom Layer with Docker
- Created a Dockerfile to build a custom layer with GDAL, rasterio, and rio-tiler
- Encountered issues with installing GDAL in the Docker container
- The build process was complex and error-prone

## Revised Strategy

### Approach 3: Using Lambda Container Images
- Instead of using a separate Lambda layer, we'll package each Lambda function as a container image
- This approach bundles all dependencies directly with the function code
- Eliminates the need for a separate layer
- Provides better isolation and consistency

### Approach 4: Simplify Processing Requirements
- For initial deployment, we can use pre-processed sample images
- This allows us to demonstrate the architecture without the complex image processing
- We can add the full processing capabilities in a future iteration

## Next Steps
1. Update the CDK stack to use Lambda functions without the external layer dependency
2. Deploy a simplified version of the backend
3. Integrate with the frontend
4. Plan for future enhancements with full image processing capabilities
