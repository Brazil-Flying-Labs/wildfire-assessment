# Google Earth Engine Satellite Imagery Implementation

## Overview

We've implemented a simplified approach to displaying satellite imagery by using Google Earth Engine's JavaScript API directly from the frontend. This bypasses the complex backend system with TiTiler, COGs, and DynamoDB for a more immediate solution.

## Why This Approach

After validating the BFL backend, we encountered issues with the Lambda function execution. The ingest Lambda was failing with runtime errors, making it difficult to get imagery into the S3 bucket for frontend display.

Rather than spending more time debugging the complex backend system, we implemented a direct GEE approach as mentioned in the project memories. This allows us to:

1. Display satellite imagery immediately without waiting for backend processing
2. Reduce complexity and potential points of failure
3. Get a working visualization that can be used while the more robust backend is fixed

## Implementation Details

### Components Created

- **GEESatelliteMap**: A React component that:
  - Loads the Google Earth Engine JavaScript API dynamically
  - Fetches Sentinel-2 imagery directly from GEE
  - Supports RGB, NDVI, and NBR visualization layers
  - Includes date selection with a 10-day window to find the least cloudy image
  - Shows cloud cover percentage for the displayed image

### Integration

- Added the GEE map component to the dashboard page
- Created a dedicated "GEE Map" tab for testing this approach
- Maintained the original satellite map component for comparison

### Technical Notes

1. The GEE JavaScript API is loaded dynamically to avoid SSR issues
2. TypeScript typings are handled with `window as any` casting since GEE doesn't provide TypeScript definitions
3. We use a 10-day window to find the least cloudy image near the selected date
4. The component handles error states and loading indicators

## Next Steps

- [x] Implement GEE Satellite Map component
- [x] Add to dashboard with dedicated tab
- [ ] Add authentication for GEE API (currently uses public access)
- [ ] Implement region boundary visualization
- [ ] Add time-series comparison for burn analysis
- [ ] Consider caching frequently viewed images for performance

## Comparison with Backend Approach

| Feature | GEE Frontend Approach | Backend Processing Approach |
|---------|----------------------|----------------------------|
| Setup Complexity | Low - just frontend code | High - AWS infrastructure, Lambdas, S3, etc. |
| Processing Control | Limited to GEE capabilities | Full control over processing pipeline |
| Cost | Free tier limitations | Pay for AWS resources |
| Performance | Depends on GEE and client | Optimized with CloudFront caching |
| Offline Support | No | Yes, with cached tiles |
| Custom Processing | Limited | Extensive |

This approach is meant as a temporary solution while we fix the more robust backend system.
