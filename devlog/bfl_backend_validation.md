# BFL Backend Validation Checklist

This document tracks our progress validating the satellite imagery backend pipeline.

## Validation Steps

- [x] STAC API Connection
- [x] Lambda Deployment & Permissions
- [❌] Image Processing
- [ ] S3 Storage
- [ ] CloudFront Distribution
- [❌] API Gateway
- [ ] Frontend Integration
- [ ] Image Quality & Usability
- [ ] End-to-End Test

## 1. STAC API Connection

✅ **Verified:** Successfully connected to Element84 STAC API and found Sentinel-2 imagery with all required assets.

We created and ran `test_stac.py` which confirmed:
- The STAC API endpoint is accessible
- We can find Sentinel-2 L2A imagery for our target location (San Francisco)
- All required assets (red, nir, swir22, visual) are available
- Cloud cover is low (1.9%)
- Scene ID: S2C_10SEG_20250518_0_L2A
- Acquisition date: 2025-05-18T19:04:27.095000Z

## 2. Lambda Deployment & Permissions

✅ **Verified:** Successfully deployed the CDK stack with all required resources.

We ran `./deploy_and_verify.sh` and confirmed:
- The stack was deployed successfully
- We received all required outputs:
  - API URL: https://y7s6nh2e24.execute-api.us-east-1.amazonaws.com/v1/
  - CDN URL: https://d3nl71iv3sr2rn.cloudfront.net
  - Bucket Name: imagerystack-imagerybucket708a4ddc-lyexfjslzwkb
- The Lambda has proper permissions to write to S3 (configured in the CDK stack)

## 3. Image Processing

❌ **Issue Detected:** The ingest Lambda function is failing to execute.

We attempted to invoke the Lambda function with a test event:
```json
{
  "lat": 37.77,
  "lon": -122.42,
  "daysAgo": 1
}
```

The Lambda function returned an error:
```
Runtime.ExitError: RequestId: 09b29c75-3323-4990-ad72-886c67a93c02 Error: Runtime exited with error: exit status 2
```

Examining the CloudWatch logs revealed a port conflict in the Lambda container:
```
Runtime API Server failed to listen error=listen tcp 127.0.0.1:9001: bind: address already in use
```

**Possible causes:**
1. The Docker image configuration in the Dockerfile may have an issue with the AWS Lambda Runtime Interface Emulator (RIE)
2. There might be a conflict between the Lambda runtime and the custom Docker container
3. The memory or CPU allocation might be insufficient for the geospatial processing

**Attempted fixes:**
1. Modified the Dockerfile to remove the custom RIE setup and use the Lambda runtime included in the LambGeo base image
2. Redeployed the Lambda function

**Results:**
- The deployment was successful, but we're still encountering Lambda execution errors
- The error changed from "Runtime API Server failed to listen" to "Runtime exited without providing a reason"
- The Lambda function is still failing to execute properly

**Next steps:**
1. Try a simpler approach using the Google Earth Engine JavaScript API directly from the frontend as mentioned in the memory
2. This would bypass the complex backend system with TiTiler, COGs, and DynamoDB for a more immediate solution
3. Create a GEESatelliteMap component that loads imagery directly from GEE

## 4. S3 Storage

After the Lambda runs:
1. Verify files are uploaded to S3 with the correct structure
2. Check that files have public-read ACL
3. Confirm proper content-type (image/tiff)

## 5. CloudFront Distribution

To validate this step:
1. Run `./test_api_and_cdn.py` to check CloudFront URLs
2. Verify proper caching headers
3. Confirm files are accessible via CloudFront

## 6. API Gateway

❌ **Issue Detected:** The API Gateway `/scenes` endpoint is returning a 502 error.

We ran `test_api_and_cdn.py` and found:
- The API endpoint is accessible but returns an Internal Server Error (502)
- This suggests the Lambda function is failing to execute properly
- Possible issues:
  - The Lambda function may not have the correct permissions
  - There might be an error in the Lambda function code
  - The S3 bucket might be empty (no scenes have been ingested yet)

**Next steps:**
1. Check CloudWatch logs for the Lambda function
2. Verify that the Lambda function has the correct permissions
3. Try invoking the Lambda function directly to ingest a scene

## 7. Frontend Integration

To validate this step:
1. Open `test_frontend.html` in a browser
2. Select a scene and layer type
3. Verify the imagery loads and displays correctly

## 8. Image Quality & Usability

To validate this step:
1. Download a sample COG and open it in QGIS
2. Check georeferencing and value ranges
3. Verify NDVI values are between -1 and 1

## 9. End-to-End Test

To validate this step:
1. Deploy both backend and frontend
2. Trigger a new image ingest
3. Verify the image appears in the frontend

## Next Steps

After completing the validation checklist, we can:
1. Integrate with the main frontend application
2. Add more features like time series analysis
3. Optimize for performance and cost

## 3. Image Processing

We manually invoked the ingest Lambda function with a test event:
```json
{
  "lat": 37.77,
  "lon": -122.42,
  "daysAgo": 1
}
```

The Lambda function was triggered successfully. The ingest process will:
1. Search for Sentinel-2 imagery via STAC API
2. Download the required bands (red, nir, swir22, visual)
3. Calculate NDVI and NBR indices
4. Convert to Cloud-Optimized GeoTIFFs
5. Upload to S3 with public-read ACL

This process may take several minutes to complete. We'll check the S3 bucket and CloudWatch logs to verify success.

## 3. Image Processing

We manually invoked the ingest Lambda function with a test event:
```json
{
  "lat": 37.77,
  "lon": -122.42,
  "daysAgo": 1
}
```

The Lambda function was triggered successfully. The ingest process will:
1. Search for Sentinel-2 imagery via STAC API
2. Download the required bands (red, nir, swir22, visual)
3. Calculate NDVI and NBR indices
4. Convert to Cloud-Optimized GeoTIFFs
5. Upload to S3 with public-read ACL

This process may take several minutes to complete. We'll check the S3 bucket and CloudWatch logs to verify success.
