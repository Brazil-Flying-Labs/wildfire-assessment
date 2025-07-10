# Phase 4: Go-Live & Monitoring

## Overview

This final phase covers the production go-live process, monitoring setup, and ongoing maintenance procedures for the AWS-hosted wildfire assessment platform. It ensures smooth transition from Vercel and establishes operational procedures.

## Prerequisites

Before starting this phase, ensure:
- [ ] Phase 1 (CDK Infrastructure) completed successfully
- [ ] Phase 2 (CI/CD Pipeline) completed successfully  
- [ ] Phase 3 (Integration & Testing) passed all criteria
- [ ] All stakeholders informed of go-live timeline
- [ ] Rollback plan prepared and tested

## Step 1: Pre-Go-Live Checklist

### 1.1 Infrastructure Readiness

**Verify all components are operational:**

```bash
# Check CloudFront distribution status
aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID \
  --query "Distribution.Status" --output text

# Verify S3 bucket configuration
aws s3api get-bucket-website --bucket wildfire-frontend-account-region

# Check SSL certificate status  
aws acm describe-certificate --certificate-arn YOUR_CERT_ARN \
  --query "Certificate.Status" --output text

# Verify Route 53 DNS configuration (if applicable)
dig wildfire.brazilflyinglabs.org +short
```

### 1.2 Performance Baseline

**Establish performance baselines:**

```bash
# Create performance monitoring script
cat > performance-baseline.js << 'EOF'
const https = require('https');

const endpoints = [
  'https://wildfire.brazilflyinglabs.org/',
  'https://wildfire.brazilflyinglabs.org/dashboard',
  'https://wildfire.brazilflyinglabs.org/monitoring/satellite'
];

async function measurePerformance(url) {
  return new Promise((resolve) => {
    const start = Date.now();
    
    https.get(url, (res) => {
      const ttfb = Date.now() - start;
      let data = '';
      
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        resolve({
          url,
          ttfb,
          status: res.statusCode,
          size: data.length,
          cacheStatus: res.headers['x-cache'] || 'Unknown'
        });
      });
    });
  });
}

async function runBaseline() {
  console.log('📊 Performance Baseline Measurement\n');
  
  for (const endpoint of endpoints) {
    const result = await measurePerformance(endpoint);
    console.log(`${endpoint}:`);
    console.log(`  TTFB: ${result.ttfb}ms`);
    console.log(`  Status: ${result.status}`);
    console.log(`  Size: ${(result.size / 1024).toFixed(2)}KB`);
    console.log(`  Cache: ${result.cacheStatus}\n`);
  }
}

runBaseline();
EOF

node performance-baseline.js
```

### 1.3 Backup and Recovery Verification

**Test backup procedures:**

```bash
# Backup current S3 bucket state
aws s3 sync s3://wildfire-frontend-account-region/ ./backup-$(date +%Y%m%d)/ 

# Test restoration procedure
aws s3 sync ./backup-$(date +%Y%m%d)/ s3://wildfire-frontend-test-account-region/
```

## Step 2: DNS Migration Strategy

### 2.1 DNS Cutover Planning

**If migrating from existing domain:**

```bash
# Check current DNS configuration
dig wildfire.brazilflyinglabs.org +short

# Prepare DNS change script
cat > dns-cutover.sh << 'EOF'
#!/bin/bash

# Current CloudFront distribution domain
CLOUDFRONT_DOMAIN="d1234567890abc.cloudfront.net"

# Update DNS record (example for Route 53)
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "wildfire.brazilflyinglabs.org",
        "Type": "CNAME", 
        "TTL": 300,
        "ResourceRecords": [{"Value": "'$CLOUDFRONT_DOMAIN'"}]
      }
    }]
  }'

echo "DNS record updated to point to CloudFront"
EOF

chmod +x dns-cutover.sh
```

### 2.2 TTL Reduction

**Reduce DNS TTL before cutover:**

```bash
# Set low TTL (5 minutes) before migration
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "wildfire.brazilflyinglabs.org",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "current-vercel-domain.vercel.app"}]
      }
    }]
  }'
```

## Step 3: Go-Live Execution

### 3.1 Final Deployment

**Execute final deployment:**

```bash
# Trigger final deployment
cd bfl-frontend
git add .
git commit -m "Final pre-go-live deployment"
git push origin main

# Monitor deployment
github_run_id=$(gh run list --workflow="Deploy Frontend to AWS" --limit=1 --json databaseId --jq '.[0].databaseId')
gh run watch $github_run_id
```

### 3.2 DNS Cutover

**Execute DNS change:**

```bash
# Execute DNS cutover
./dns-cutover.sh

# Monitor DNS propagation
while true; do
  result=$(dig wildfire.brazilflyinglabs.org +short)
  echo "$(date): DNS resolves to: $result"
  sleep 30
done
```

### 3.3 Verification Post-Cutover

**Immediate verification steps:**

```bash
# Test from multiple locations
for location in us-east-1 us-west-2 eu-west-1; do
  echo "Testing from $location:"
  curl -s -o /dev/null -w "HTTP: %{http_code}, Time: %{time_total}s\n" \
    https://wildfire.brazilflyinglabs.org/
done

# Verify SSL certificate
openssl s_client -connect wildfire.brazilflyinglabs.org:443 -servername wildfire.brazilflyinglabs.org < /dev/null
```

## Step 4: Monitoring Setup

### 4.1 CloudWatch Dashboards

**Create monitoring dashboard:**

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/CloudFront", "Requests", "DistributionId", "YOUR_DISTRIBUTION_ID"],
          ["AWS/CloudFront", "BytesDownloaded", "DistributionId", "YOUR_DISTRIBUTION_ID"]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "CloudFront Traffic"
      }
    },
    {
      "type": "metric", 
      "properties": {
        "metrics": [
          ["AWS/CloudFront", "CacheHitRate", "DistributionId", "YOUR_DISTRIBUTION_ID"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1", 
        "title": "Cache Performance"
      }
    }
  ]
}
```

**Deploy dashboard:**

```bash
# Save as cloudfront-dashboard.json and deploy
aws cloudwatch put-dashboard \
  --dashboard-name "Wildfire-Frontend-Monitoring" \
  --dashboard-body file://cloudfront-dashboard.json
```

### 4.2 CloudWatch Alarms

**Create critical alarms:**

```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "Wildfire-Frontend-High-Error-Rate" \
  --alarm-description "High 4xx/5xx error rate" \
  --metric-name ErrorRate \
  --namespace AWS/CloudFront \
  --statistic Average \
  --period 300 \
  --threshold 5.0 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=DistributionId,Value=YOUR_DISTRIBUTION_ID \
  --evaluation-periods 2

# Low cache hit rate alarm  
aws cloudwatch put-metric-alarm \
  --alarm-name "Wildfire-Frontend-Low-Cache-Hit-Rate" \
  --alarm-description "CloudFront cache hit rate below 70%" \
  --metric-name CacheHitRate \
  --namespace AWS/CloudFront \
  --statistic Average \
  --period 900 \
  --threshold 70.0 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=DistributionId,Value=YOUR_DISTRIBUTION_ID \
  --evaluation-periods 3
```

### 4.3 Application-Level Monitoring

**Create uptime monitoring script:**

```bash
cat > uptime-monitor.sh << 'EOF'
#!/bin/bash

URL="https://wildfire.brazilflyinglabs.org"
LOG_FILE="/var/log/wildfire-uptime.log"

check_health() {
  local start_time=$(date +%s.%N)
  local response=$(curl -s -o /dev/null -w "%{http_code},%{time_total}" "$URL")
  local end_time=$(date +%s.%N)
  
  local http_code=$(echo $response | cut -d, -f1)
  local response_time=$(echo $response | cut -d, -f2)
  
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  if [ "$http_code" = "200" ]; then
    echo "$timestamp,UP,$http_code,$response_time" >> $LOG_FILE
  else
    echo "$timestamp,DOWN,$http_code,$response_time" >> $LOG_FILE
    # Send alert (integrate with your notification system)
    echo "ALERT: Site down - HTTP $http_code" | mail -s "Wildfire Site Alert" ops@yourorg.com
  fi
}

# Run check
check_health
EOF

# Set up cron job for monitoring
echo "*/5 * * * * /path/to/uptime-monitor.sh" | crontab -
```

## Step 5: Performance Optimization

### 5.1 CloudFront Optimization

**Optimize caching policies:**

```bash
# Create optimized cache policy
aws cloudfront create-cache-policy \
  --cache-policy-config '{
    "Name": "WildfireOptimizedCaching",
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "MinTTL": 0,
    "ParametersInCacheKeyAndForwardedToOrigin": {
      "EnableAcceptEncodingGzip": true,
      "EnableAcceptEncodingBrotli": true,
      "QueryStringsConfig": {
        "QueryStringBehavior": "none"
      },
      "HeadersConfig": {
        "HeaderBehavior": "none"
      },
      "CookiesConfig": {
        "CookieBehavior": "none"
      }
    }
  }'
```

### 5.2 S3 Transfer Acceleration

**Enable S3 Transfer Acceleration if needed:**

```bash
# Enable transfer acceleration for deployment bucket
aws s3api put-bucket-accelerate-configuration \
  --bucket wildfire-frontend-account-region \
  --accelerate-configuration Status=Enabled
```

## Step 6: Security Hardening

### 6.1 Security Headers

**Add security headers via CloudFront:**

```json
{
  "ResponseHeadersPolicy": {
    "Name": "WildfireSecurityHeaders",
    "SecurityHeadersConfig": {
      "StrictTransportSecurity": {
        "AccessControlMaxAgeSec": 31536000,
        "IncludeSubdomains": true
      },
      "ContentTypeOptions": {
        "Override": true
      },
      "FrameOptions": {
        "FrameOption": "SAMEORIGIN",
        "Override": true
      },
      "XSSProtection": {
        "ModeBlock": true,
        "Protection": true,
        "Override": true
      }
    }
  }
}
```

### 6.2 WAF Configuration (Optional)

**Set up AWS WAF for additional protection:**

```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name WildfireFrontendWAF \
  --scope CLOUDFRONT \
  --default-action Allow={} \
  --rules '[
    {
      "Name": "RateLimitRule",
      "Priority": 1,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {
        "Block": {}
      },
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimitRule"
      }
    }
  ]'
```

## Step 7: Documentation and Handover

### 7.1 Operations Runbook

**Create operations documentation:**

```markdown
# Wildfire Frontend Operations Runbook

## Emergency Contacts
- DevOps Lead: your-email@domain.com
- AWS Account Owner: aws-admin@domain.com

## Critical Procedures

### Rollback Procedure
1. Revert DNS to previous configuration
2. Deploy previous version from backup
3. Invalidate CloudFront cache

### Cache Issues
- Clear CloudFront cache: `aws cloudfront create-invalidation --distribution-id ID --paths "/*"`
- Check cache hit rates in CloudWatch

### Performance Issues  
- Monitor CloudFront metrics
- Check origin health
- Verify DNS resolution

## Monitoring Dashboards
- CloudWatch: Wildfire-Frontend-Monitoring
- Uptime: /var/log/wildfire-uptime.log
```

### 7.2 Maintenance Procedures

**Schedule regular maintenance:**

```bash
# Weekly maintenance script
cat > weekly-maintenance.sh << 'EOF'
#!/bin/bash

echo "🔧 Starting weekly maintenance..."

# Clean up old deployment artifacts
aws s3 rm s3://wildfire-frontend-account-region/maintenance/ --recursive

# Review CloudWatch logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/frontend-functions \
  --start-time $(date -d '7 days ago' +%s)000 \
  --filter-pattern "ERROR"

# Check SSL certificate expiration
aws acm describe-certificate \
  --certificate-arn YOUR_CERT_ARN \
  --query "Certificate.NotAfter"

echo "✅ Weekly maintenance completed"
EOF
```

## Step 8: Post-Go-Live Monitoring

### 8.1 First 24 Hours

**Intensive monitoring checklist:**

- [ ] Monitor error rates every 15 minutes
- [ ] Check performance metrics hourly
- [ ] Verify user feedback channels
- [ ] Monitor cost implications
- [ ] Check DNS propagation globally

### 8.2 First Week

**Extended monitoring:**

- [ ] Daily performance reviews
- [ ] Weekly cost analysis
- [ ] User experience feedback collection
- [ ] Security scan results review

### 8.3 Ongoing Monitoring

**Monthly tasks:**

- [ ] Cost optimization review
- [ ] Performance trend analysis
- [ ] Security updates and patches
- [ ] Backup verification tests

## Success Criteria

### Technical Success
- [ ] Site loads consistently under 3 seconds
- [ ] 99.9% uptime achieved
- [ ] Cache hit rate above 85%
- [ ] Error rate below 0.1%
- [ ] All monitoring and alerts functional

### Business Success
- [ ] Zero user complaints about performance
- [ ] Cost targets met or exceeded
- [ ] All stakeholders satisfied with migration
- [ ] Documentation complete and accessible

## Rollback Plan

### Emergency Rollback

If critical issues arise:

```bash
# 1. Immediate DNS rollback
aws route53 change-resource-record-sets \
  --hosted-zone-id YOUR_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "wildfire.brazilflyinglabs.org",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "previous-vercel-domain.vercel.app"}]
      }
    }]
  }'

# 2. Notify stakeholders
echo "Emergency rollback executed at $(date)" | mail -s "URGENT: Wildfire Site Rollback" stakeholders@domain.com

# 3. Investigate issues
# 4. Plan remediation
```

## Cost Optimization

### Post-Go-Live Cost Review

**Monthly cost analysis:**

```bash
# Get CloudFront costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Review S3 costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon Simple Storage Service"]
    }
  }'
```

## Conclusion

The successful completion of Phase 4 marks the full migration from Vercel to AWS. The wildfire assessment platform is now:

- Fully hosted on AWS infrastructure
- Integrated with existing backend services  
- Monitored and alerting configured
- Optimized for performance and cost
- Secured with industry best practices
- Documented for ongoing operations

The platform is ready for production use by Brazil Flying Labs and their stakeholders.

---

*Estimated Duration: 4-6 hours (plus 24-48 hours of intensive monitoring)*
*Go-Live Validation Period: 1 week*