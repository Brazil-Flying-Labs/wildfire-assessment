# Google Earth Engine Export API Implementation

## Overview
Implemented a solution to use Google Earth Engine's Export API to generate and display satellite imagery. This approach leverages the Earth Engine Python API on the backend to export imagery and serve it to the frontend.

## Implementation Details

- [x] Created a backend API endpoint (`/api/gee-export/route.ts`) that:
  - Accepts parameters for region, date range, and visualization layer
  - Uses the service account credentials to authenticate with Earth Engine
  - Generates a Python script to run the Earth Engine export process
  - Returns the URL of the exported image

- [x] Created a frontend component (`GEEExportMap`) that:
  - Uses Leaflet for the base map functionality
  - Makes requests to the backend API to generate satellite imagery
  - Provides controls for selecting different visualization layers (RGB, NDVI, NBR)
  - Includes date selection for finding imagery within specific time periods
  - Displays loading states and error messages

- [x] Updated the dashboard to use the new GEE Export Map component

## Technical Approach

The solution works by:

1. Frontend sends a request to the backend with parameters (region, dates, layer type)
2. Backend creates a temporary Python script that:
   - Authenticates with Earth Engine using the service account
   - Queries Sentinel-2 imagery for the specified region and date range
   - Applies the appropriate visualization (RGB, NDVI, NBR)
   - Exports the image to Google Drive
   - Returns a reference to the exported image

3. Frontend displays the exported image overlaid on a Leaflet map

## Benefits of This Approach

- Properly handles authentication with Google Earth Engine
- Leverages the full power of the Earth Engine Python API
- Avoids browser-side API limitations and CORS issues
- Provides a clean separation between frontend and backend concerns

## Next Steps

- [ ] Implement proper image download from Google Drive after export completes
- [ ] Add caching for exported images to improve performance
- [ ] Implement region boundary visualization
- [ ] Add more advanced visualization options and parameters
- [ ] Create a more robust error handling and retry mechanism

## References
- [Google Earth Engine Python API](https://developers.google.com/earth-engine/guides/python_install)
- [Earth Engine Export Tasks](https://developers.google.com/earth-engine/guides/exporting)
- [Leaflet Documentation](https://leafletjs.com/reference.html)
