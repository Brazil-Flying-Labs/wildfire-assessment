# Phase 3: Integration & Testing

## Overview

This phase focuses on thorough testing of the deployed frontend with the existing AWS backend infrastructure, ensuring all satellite imagery functionality works correctly and performance meets requirements.

## Prerequisites

Before starting this phase, ensure:
- [ ] Phase 1 (CDK Infrastructure) completed successfully
- [ ] Phase 2 (CI/CD Pipeline) completed successfully  
- [ ] Frontend is deployed and accessible via CloudFront
- [ ] Backend services are operational and tested

## Step 1: Backend Integration Verification

### 1.1 API Connectivity Testing

**Test API Gateway Connection:**

```bash
# Test from deployed frontend domain
curl -X GET "https://your-distribution.cloudfront.net/api/health" -H "Accept: application/json"

# Test direct API Gateway endpoint
curl -X GET "https://your-api-gateway.execute-api.us-east-1.amazonaws.com/v1/health" -H "Accept: application/json"
```

**Verify CORS Configuration:**

Create test file: `test-cors.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>CORS Test</title>
</head>
<body>
    <script>
        fetch('https://your-api-gateway.execute-api.us-east-1.amazonaws.com/v1/health')
            .then(response => response.json())
            .then(data => console.log('Success:', data))
            .catch(error => console.error('CORS Error:', error));
    </script>
</body>
</html>
```

### 1.2 Environment Variables Validation

**File**: `bfl-frontend/scripts/validate-env.js`

```javascript
#!/usr/bin/env node

const requiredEnvVars = [
  'NEXT_PUBLIC_API_BASE_URL',
  'NEXT_PUBLIC_IMAGERY_BUCKET', 
  'NEXT_PUBLIC_CDN_URL'
];

console.log('🔍 Validating environment variables...\n');

let allValid = true;

requiredEnvVars.forEach(envVar => {
  const value = process.env[envVar];
  if (!value) {
    console.log(`❌ ${envVar}: Missing`);
    allValid = false;
  } else {
    console.log(`✅ ${envVar}: ${value}`);
  }
});

if (!allValid) {
  console.log('\n❌ Environment validation failed');
  process.exit(1);
} else {
  console.log('\n✅ All environment variables are set correctly');
}
```

**Run validation:**
```bash
cd bfl-frontend
node scripts/validate-env.js
```

## Step 2: Satellite Imagery Functionality Testing

### 2.1 Google Earth Engine Integration Testing

**Test GEE Authentication:**

Create test script: `test-gee-auth.js`
```javascript
// Test GEE authentication endpoint
async function testGEEAuth() {
  try {
    const response = await fetch('/api/gee-auth', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    console.log('GEE Auth Response:', data);
    return response.ok;
  } catch (error) {
    console.error('GEE Auth Error:', error);
    return false;
  }
}

testGEEAuth();
```

### 2.2 Satellite Map Component Testing

**Test satellite map loading:**

```javascript
// Test satellite imagery endpoints
const testEndpoints = [
  '/api/gee-init',
  '/api/gee-export', 
  '/api/valid-dates',
  '/api/burnSeverity'
];

async function testEndpoints() {
  for (const endpoint of testEndpoints) {
    try {
      const response = await fetch(endpoint);
      console.log(`${endpoint}: ${response.status} ${response.statusText}`);
    } catch (error) {
      console.error(`${endpoint}: Error - ${error.message}`);
    }
  }
}
```

### 2.3 Image Processing Pipeline Testing

**Test NDVI/NBR calculation workflow:**

```bash
# Test Sentinel-2 data processing
curl -X POST "https://your-api-gateway.amazonaws.com/v1/gee-export" \
  -H "Content-Type: application/json" \
  -d '{
    "coordinates": [[-48.0, -15.0], [-47.0, -14.0]],
    "startDate": "2024-01-01",
    "endDate": "2024-01-31"
  }'
```

## Step 3: Performance Testing

### 3.1 CloudFront Performance Testing

**Test caching behavior:**

```bash
# Test static asset caching
curl -I "https://your-distribution.cloudfront.net/_next/static/css/app.css"

# Test HTML caching
curl -I "https://your-distribution.cloudfront.net/"

# Test API proxying
curl -I "https://your-distribution.cloudfront.net/api/health"
```

### 3.2 Load Testing

**Create simple load test script: `load-test.js`**

```javascript
const https = require('https');

const baseUrl = 'https://your-distribution.cloudfront.net';
const endpoints = ['/', '/dashboard', '/monitoring/satellite'];

async function makeRequest(url) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    
    https.get(url, (res) => {
      const duration = Date.now() - start;
      resolve({
        url,
        status: res.statusCode,
        duration,
        headers: res.headers
      });
    }).on('error', reject);
  });
}

async function runLoadTest() {
  console.log('🚀 Starting load test...\n');
  
  for (const endpoint of endpoints) {
    const url = baseUrl + endpoint;
    const requests = Array(10).fill().map(() => makeRequest(url));
    
    try {
      const results = await Promise.all(requests);
      const avgDuration = results.reduce((sum, r) => sum + r.duration, 0) / results.length;
      
      console.log(`📊 ${endpoint}:`);
      console.log(`   Average response time: ${avgDuration.toFixed(2)}ms`);
      console.log(`   All requests successful: ${results.every(r => r.status === 200)}`);
      console.log('');
    } catch (error) {
      console.error(`❌ Error testing ${endpoint}:`, error.message);
    }
  }
}

runLoadTest();
```

**Run load test:**
```bash
node load-test.js
```

### 3.3 Image Loading Performance

**Test satellite imagery loading times:**

```javascript
// Browser performance test
function testImageLoading() {
  const testImages = [
    'https://your-imagery-bucket.s3.amazonaws.com/test-image-1.tif',
    'https://your-imagery-bucket.s3.amazonaws.com/test-image-2.tif'
  ];
  
  testImages.forEach((src, index) => {
    const img = new Image();
    const start = performance.now();
    
    img.onload = () => {
      const duration = performance.now() - start;
      console.log(`Image ${index + 1} loaded in ${duration.toFixed(2)}ms`);
    };
    
    img.onerror = () => {
      console.error(`Failed to load image ${index + 1}`);
    };
    
    img.src = src;
  });
}
```

## Step 4: User Experience Testing

### 4.1 Map Functionality Testing

**Test checklist for satellite map features:**

- [ ] Map loads and displays correctly
- [ ] Zoom controls work properly
- [ ] Pan functionality works smoothly
- [ ] Layer controls toggle correctly
- [ ] Time comparison controls function
- [ ] Download functionality works
- [ ] Filtering options work correctly

### 4.2 Responsive Design Testing

**Test on different viewport sizes:**

```javascript
// Automated responsive testing script
const viewports = [
  { width: 320, height: 568, name: 'Mobile' },
  { width: 768, height: 1024, name: 'Tablet' },
  { width: 1024, height: 768, name: 'Tablet Landscape' },
  { width: 1920, height: 1080, name: 'Desktop' }
];

// Test each viewport (if using Puppeteer)
for (const viewport of viewports) {
  await page.setViewport(viewport);
  await page.goto('https://your-distribution.cloudfront.net/');
  
  // Take screenshot for manual review
  await page.screenshot({ 
    path: `screenshots/${viewport.name.toLowerCase()}.png`,
    fullPage: true 
  });
}
```

### 4.3 Accessibility Testing

**Basic accessibility checks:**

```javascript
// Check for accessibility issues
function checkAccessibility() {
  const issues = [];
  
  // Check for missing alt attributes
  const images = document.querySelectorAll('img:not([alt])');
  if (images.length > 0) {
    issues.push(`${images.length} images missing alt attributes`);
  }
  
  // Check for heading hierarchy
  const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
  // Add heading hierarchy validation logic
  
  // Check for form labels
  const inputs = document.querySelectorAll('input:not([id])');
  if (inputs.length > 0) {
    issues.push(`${inputs.length} inputs without proper labels`);
  }
  
  return issues;
}
```

## Step 5: Integration with Backend Services

### 5.1 Step Functions Integration Testing

**Test the satellite processing workflow:**

```bash
# Start a Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn "arn:aws:states:region:account:stateMachine:YourStateMachine" \
  --input '{
    "region": "test-region",
    "startDate": "2024-01-01", 
    "endDate": "2024-01-31"
  }'
```

### 5.2 S3 Batch Operations Testing

**Verify batch processing results:**

```bash
# Check batch processing outputs
aws s3 ls s3://bfl-satellite-imagery-account-id/processed/ --recursive

# Verify GeoTIFF file integrity
aws s3 cp s3://bfl-satellite-imagery-account-id/processed/sample.tif ./test.tif
# Use GDAL tools to verify file integrity
```

### 5.3 Lambda Function Integration

**Test Lambda function responses:**

```bash
# Test individual Lambda functions
aws lambda invoke \
  --function-name gee-export-function \
  --payload '{"test": "data"}' \
  response.json

cat response.json
```

## Step 6: Error Handling Testing

### 6.1 Network Error Simulation

**Test offline scenarios:**

```javascript
// Test offline behavior
if ('serviceWorker' in navigator) {
  // Simulate offline conditions
  window.addEventListener('offline', () => {
    console.log('App is offline');
    // Test offline UI behavior
  });
  
  window.addEventListener('online', () => {
    console.log('App is back online');
    // Test reconnection behavior
  });
}
```

### 6.2 API Error Handling

**Test API error responses:**

```javascript
// Test various error scenarios
const errorTests = [
  { endpoint: '/api/invalid-endpoint', expectedStatus: 404 },
  { endpoint: '/api/gee-auth', method: 'DELETE', expectedStatus: 405 },
  { endpoint: '/api/gee-export', payload: 'invalid-json', expectedStatus: 400 }
];

async function testErrorHandling() {
  for (const test of errorTests) {
    try {
      const response = await fetch(test.endpoint, {
        method: test.method || 'GET',
        body: test.payload
      });
      
      console.log(`${test.endpoint}: ${response.status} (expected: ${test.expectedStatus})`);
    } catch (error) {
      console.log(`${test.endpoint}: Network error - ${error.message}`);
    }
  }
}
```

## Step 7: Monitoring and Observability Testing

### 7.1 CloudWatch Metrics Verification

**Check CloudFront metrics:**

```bash
# Get CloudFront metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --dimensions Name=DistributionId,Value=YOUR_DISTRIBUTION_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### 7.2 Application Performance Monitoring

**Test performance monitoring:**

```javascript
// Performance monitoring script
function monitorPerformance() {
  // Monitor Core Web Vitals
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      console.log(`${entry.name}: ${entry.value}`);
    }
  }).observe({ entryTypes: ['web-vital'] });
  
  // Monitor resource loading
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.duration > 1000) {
        console.warn(`Slow resource: ${entry.name} (${entry.duration}ms)`);
      }
    }
  }).observe({ entryTypes: ['resource'] });
}
```

## Step 8: Security Testing

### 8.1 Content Security Policy Testing

**Verify CSP headers:**

```bash
curl -I "https://your-distribution.cloudfront.net/" | grep -i "content-security-policy"
```

### 8.2 HTTPS and Security Headers

**Security headers checklist:**

```bash
# Test security headers
curl -I "https://your-distribution.cloudfront.net/" | grep -E "(strict-transport-security|x-content-type-options|x-frame-options|x-xss-protection)"
```

## Success Criteria

### Functional Testing
- [ ] All API endpoints respond correctly
- [ ] Satellite imagery loads and displays properly
- [ ] Map controls function as expected
- [ ] Data download functionality works
- [ ] Error handling works correctly

### Performance Testing  
- [ ] Page load times under 3 seconds
- [ ] CloudFront cache hit ratio > 80%
- [ ] API response times under 500ms
- [ ] Image loading optimized

### Integration Testing
- [ ] Frontend connects to backend APIs successfully
- [ ] Google Earth Engine integration works
- [ ] Step Functions workflow completes
- [ ] S3 batch operations process correctly

### Security Testing
- [ ] All connections use HTTPS
- [ ] Security headers properly configured
- [ ] No sensitive data exposed in frontend
- [ ] CORS properly configured

## Troubleshooting Common Issues

### API Connection Issues
```bash
# Debug CORS issues
curl -X OPTIONS "https://your-api-gateway.amazonaws.com/v1/health" \
  -H "Origin: https://your-distribution.cloudfront.net" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

### Performance Issues
```bash
# Test CloudFront edge locations
dig your-distribution.cloudfront.net
nslookup your-distribution.cloudfront.net
```

### Caching Issues
```bash
# Force cache invalidation
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

## Next Steps

Once Phase 3 is complete, proceed to [Phase 4: Go-Live & Monitoring](./phase-4-golive-monitoring.md).

---

*Estimated Duration: 6-8 hours (including comprehensive testing)*