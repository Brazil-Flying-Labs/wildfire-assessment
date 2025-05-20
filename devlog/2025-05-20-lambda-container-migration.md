# Lambda Container Migration

## 2025-05-20: Migrating to Container-based Lambda Functions

### Tasks Completed
- [x] Updated all Lambda function Dockerfiles to use Python 3.10 base image
- [x] Added build toolchain to compile dependencies (gcc, g++, make)
- [x] Fixed dependency installation issues with rasterio and numexpr
- [x] Updated CDK stack to use Python 3.10 runtime
- [x] Successfully built all Lambda function Docker images locally
  - rgb-local: 517MB
  - ndvi-local: 517MB
  - nbr-local: 517MB
  - diff-local: 517MB

### Technical Details

We encountered several challenges when migrating to container-based Lambda functions:

1. **Wheel Compatibility**: Initially, we tried using rasterio 1.3.11 and 1.3.6, but these versions don't have pre-built wheels for Python 3.10. We then tried rasterio 1.4.3, which has wheels available but faced issues with the manylinux tag format.

2. **Build Environment**: We needed to include the full build toolchain (gcc, g++, make) to compile numexpr, which is a dependency of rio-tiler. This approach allows us to use the latest versions of all dependencies without relying on pre-built wheels.

3. **Architecture Considerations**: When building on ARM-based Macs (M1/M2), we need to use the `--platform=linux/amd64` flag with Docker to ensure compatibility with AWS Lambda's x86_64 architecture.

4. **Image Size Optimization**: We remove the build toolchain after installing dependencies to reduce the final image size.

### Final Approach

Our final Dockerfile approach:

```dockerfile
# Use --platform=linux/amd64 when building on ARM Macs
FROM public.ecr.aws/lambda/python:3.10

# Install build toolchain
RUN yum install -y gcc gcc-c++ make

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build toolchain to slim the image
RUN yum remove -y gcc gcc-c++ make && yum clean all

COPY handler.py .
CMD ["handler.main"]
```

This approach successfully builds all dependencies, including rasterio and rio-tiler, without requiring Lambda layers.

### Next Steps
- [x] Update CDK stack to use Docker container images
- [ ] Deploy the updated Lambda functions to AWS
  ```bash
  # Build Docker images for Lambda functions
  cd lambda/rgb && docker build --platform=linux/amd64 -t rgb-lambda .
  cd ../ndvi && docker build --platform=linux/amd64 -t ndvi-lambda .
  cd ../nbr && docker build --platform=linux/amd64 -t nbr-lambda .
  cd ../diff && docker build --platform=linux/amd64 -t diff-lambda .
  cd ../..
  
  # Deploy CDK stack
  npm run deploy
  ```
- [ ] Test the functions in the AWS environment
- [ ] Monitor performance and cold start times
- [ ] Update documentation with the new deployment process
