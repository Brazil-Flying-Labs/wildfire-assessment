# TiTiler Integration Fixes - 2025-05-15

## Issue Description
The satellite map component was encountering 404 errors when trying to load imagery from the TiTiler API. The root cause was a mismatch between the asset path formats used by the frontend and expected by the backend, as well as issues with the DynamoDB table not being properly populated with valid dates for imagery.

## Investigation Findings

- [x] Identified that the DynamoDB table wasn't being populated correctly with valid dates
- [x] Found a mismatch between the asset path formats used by the frontend and expected by the backend
- [x] Discovered that the TiTiler handler in the backend wasn't flexible enough in handling different asset path formats
- [x] Determined that the frontend needed better fallback mechanisms for when valid dates aren't available

## Changes Made

### Backend Changes

1. **TiTiler Handler Improvements**:
   - Added support for multiple asset path formats:
     - Format 1: `processed/{areaId}/{date}/{LAYER}.tif`
     - Format 2: `{areaId}/{date}_{LAYER}.tif`
     - Format 3: `{areaId}/{date}.tif`
   - Implemented a flexible approach that tries multiple formats if the first one fails
   - Added more detailed logging to help diagnose issues
   - Enhanced error handling to provide more informative error messages

### Frontend Changes

1. **Satellite Map Component**:
   - Added a fallback mechanism using hardcoded known valid dates
   - Implemented a more robust approach to finding the closest valid date for imagery
   - Added detailed logging to track the asset path construction and API calls

2. **TiTiler API Route**:
   - Enhanced the proxy route to better handle different asset path formats
   - Added special handling for 404 errors to provide more helpful error messages
   - Implemented a helper function to find the closest valid date when the requested date isn't available

## Next Steps

- [ ] Deploy the backend changes to AWS
- [ ] Test the TiTiler integration with the updated backend
- [ ] Monitor the logs to ensure that the asset paths are being handled correctly
- [ ] Investigate why the DynamoDB table isn't being populated correctly with valid dates
- [ ] Consider implementing a more robust mechanism for tracking and querying valid dates

## Technical Details

The key issue was in how asset paths were being constructed and handled. The backend expected a specific format, but the frontend was using a different format. We've made both sides more flexible to handle multiple formats, with fallbacks in place for when the preferred format isn't available.

We've also added more detailed logging throughout the system to help diagnose any future issues.
