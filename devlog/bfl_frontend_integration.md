# BFL Frontend Integration

## Overview
Integrating the BFL backend satellite imagery products into the frontend dashboard.

## Changes Made
- [x] Created a new "Fire Products" tab in the dashboard
- [x] Added UI components to display RGB, NDVI, and NBR products
- [x] Implemented difference analysis with baseline comparison
- [x] Added date selection controls
- [x] Installed missing dependencies for UI components

## Implementation Details
- Added a new tab in the dashboard to display satellite imagery products from the BFL backend
- Created UI for viewing RGB, NDVI, and NBR products with date selection
- Implemented difference analysis to compare images between dates
- Added error handling for missing images

## Next Steps
- Install required dependencies: `@radix-ui/react-select`
- Test the integration with real data from the BFL backend
- Add loading states and better error handling
- Improve the UI for mobile devices

## Technical Notes
- The BFL backend provides satellite imagery products at the following URLs:
  - RGB: `https://fire-products.s3.amazonaws.com/{area}/{date}/rgb.png`
  - NDVI: `https://fire-products.s3.amazonaws.com/{area}/{date}/ndvi.png`
  - NBR: `https://fire-products.s3.amazonaws.com/{area}/{date}/nbr.png`
  - Differences: `https://fire-products.s3.amazonaws.com/{area}/{date}/d{INDEX}.png`
- We're using environment variables to configure the bucket URL:
  - `NEXT_PUBLIC_BFL_BUCKET`: The S3 bucket URL for the BFL products
  - `NEXT_PUBLIC_BFL_DIFF_FUNCTION`: The Function URL for calculating differences (not used yet)
