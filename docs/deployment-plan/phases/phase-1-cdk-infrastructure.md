# Phase 1: CDK Infrastructure Setup

## Overview

This phase focuses on extending the existing CDK infrastructure to support the frontend deployment. We'll create a new CDK stack that provisions S3 bucket, CloudFront distribution, SSL certificate, and DNS configuration.

## Prerequisites

Before starting this phase, ensure:
- [ ] AWS CLI configured with deployment credentials
- [ ] CDK bootstrap completed in target region
- [ ] Existing backend CDK stack is deployed successfully
- [ ] Domain name decided and DNS management access available

## Step 1: Fix Existing Infrastructure Issues

### 1.1 Update Hardcoded VPC/Subnet IDs

**Location**: `bfl-backend/cdk/bin/app.ts:9-13`

**Current Issue**: The backend stack has hardcoded VPC and subnet IDs that need to be parameterized.

**Action Required**:
```typescript
// Before (hardcoded)
const vpcId = 'vpc-0e21d3f08ee49572b';
const subnetIds = ['subnet-0ea02d54ffe1b12b4', 'subnet-0114ece9f119f3ae5'];

// After (parameterized)
const vpcId = app.node.tryGetContext('vpcId') || 'vpc-0e21d3f08ee49572b';
const subnetIds = app.node.tryGetContext('subnetIds')?.split(',') || 
  ['subnet-0ea02d54ffe1b12b4', 'subnet-0114ece9f119f3ae5'];
```

**Context Configuration** (`cdk.json`):
```json
{
  "context": {
    "vpcId": "vpc-0e21d3f08ee49572b",
    "subnetIds": "subnet-0ea02d54ffe1b12b4,subnet-0114ece9f119f3ae5"
  }
}
```

### 1.2 Verify Existing Resources

**Commands to run**:
```bash
cd bfl-backend/cdk
aws ec2 describe-vpcs --vpc-ids vpc-0e21d3f08ee49572b
aws ec2 describe-subnets --subnet-ids subnet-0ea02d54ffe1b12b4 subnet-0114ece9f119f3ae5
```

## Step 2: Create Frontend CDK Stack

### 2.1 Create Frontend Stack File

**File**: `bfl-backend/cdk/lib/frontend-stack.ts`

```typescript
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets = 'aws-cdk-lib/aws-route53-targets';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface FrontendStackProps extends cdk.StackProps {
  domainName: string;
  hostedZoneId?: string;
  certificateArn?: string;
}

export class FrontendStack extends cdk.Stack {
  public readonly distribution: cloudfront.Distribution;
  public readonly bucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    // S3 Bucket for static website hosting
    this.bucket = new s3.Bucket(this, 'FrontendBucket', {
      bucketName: `wildfire-frontend-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
    });

    // Origin Access Identity for CloudFront
    const oai = new cloudfront.OriginAccessIdentity(this, 'FrontendOAI', {
      comment: `OAI for ${props.domainName}`,
    });

    // Grant CloudFront access to S3 bucket
    this.bucket.addToResourcePolicy(
      new iam.PolicyStatement({
        actions: ['s3:GetObject'],
        resources: [this.bucket.arnForObjects('*')],
        principals: [oai.grantPrincipal],
      })
    );

    // SSL Certificate (if not provided)
    let certificate: acm.ICertificate;
    if (props.certificateArn) {
      certificate = acm.Certificate.fromCertificateArn(
        this, 
        'Certificate', 
        props.certificateArn
      );
    } else {
      certificate = new acm.Certificate(this, 'FrontendCertificate', {
        domainName: props.domainName,
        validation: acm.CertificateValidation.fromDns(),
      });
    }

    // CloudFront Distribution
    this.distribution = new cloudfront.Distribution(this, 'FrontendDistribution', {
      defaultRootObject: 'index.html',
      domainNames: [props.domainName],
      certificate: certificate,
      defaultBehavior: {
        origin: new origins.S3Origin(this.bucket, {
          originAccessIdentity: oai,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
      },
      additionalBehaviors: {
        '/api/*': {
          origin: new origins.HttpOrigin('your-api-gateway-domain.execute-api.us-east-1.amazonaws.com'),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          originRequestPolicy: cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
        },
      },
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
      ],
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100, // US, Canada, Europe
    });

    // Route 53 DNS Record
    if (props.hostedZoneId) {
      const hostedZone = route53.HostedZone.fromHostedZoneId(
        this, 
        'HostedZone', 
        props.hostedZoneId
      );

      new route53.ARecord(this, 'FrontendAliasRecord', {
        zone: hostedZone,
        recordName: props.domainName,
        target: route53.RecordTarget.fromAlias(
          new targets.CloudFrontTarget(this.distribution)
        ),
      });
    }

    // SSM Parameters for CI/CD pipeline
    new ssm.StringParameter(this, 'FrontendBucketName', {
      parameterName: '/wildfire/frontend/bucket-name',
      stringValue: this.bucket.bucketName,
      description: 'S3 bucket name for frontend static assets',
    });

    new ssm.StringParameter(this, 'FrontendDistributionId', {
      parameterName: '/wildfire/frontend/distribution-id',
      stringValue: this.distribution.distributionId,
      description: 'CloudFront distribution ID for cache invalidation',
    });

    new ssm.StringParameter(this, 'FrontendDomainName', {
      parameterName: '/wildfire/frontend/domain-name',
      stringValue: this.distribution.distributionDomainName,
      description: 'CloudFront distribution domain name',
    });

    // Outputs
    new cdk.CfnOutput(this, 'BucketName', {
      value: this.bucket.bucketName,
      description: 'Frontend S3 bucket name',
    });

    new cdk.CfnOutput(this, 'DistributionId', {
      value: this.distribution.distributionId,
      description: 'CloudFront distribution ID',
    });

    new cdk.CfnOutput(this, 'DistributionDomainName', {
      value: this.distribution.distributionDomainName,
      description: 'CloudFront distribution domain name',
    });

    new cdk.CfnOutput(this, 'WebsiteURL', {
      value: `https://${props.domainName}`,
      description: 'Frontend website URL',
    });
  }
}
```

### 2.2 Update Main CDK App

**File**: `bfl-backend/cdk/bin/app.ts`

```typescript
import { FrontendStack } from '../lib/frontend-stack';

// Add after existing stack instantiation
const frontendStack = new FrontendStack(app, 'WildfireFrontendStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  domainName: 'wildfire.brazilflyinglabs.org', // Update with your domain
  // hostedZoneId: 'Z1234567890', // Add if using Route 53
});
```

### 2.3 Update Package Dependencies

**File**: `bfl-backend/cdk/package.json`

Add any missing dependencies:
```json
{
  "dependencies": {
    "aws-cdk-lib": "^2.100.0",
    "@aws-cdk/aws-cloudfront-origins": "^2.100.0"
  }
}
```

## Step 3: Deploy Infrastructure

### 3.1 Install Dependencies
```bash
cd bfl-backend/cdk
npm install
```

### 3.2 Review Changes
```bash
cdk diff WildfireFrontendStack
```

### 3.3 Deploy Frontend Stack
```bash
cdk deploy WildfireFrontendStack
```

**Expected Output**:
```
WildfireFrontendStack.BucketName = wildfire-frontend-123456789-us-east-1
WildfireFrontendStack.DistributionId = E1234567890ABC
WildfireFrontendStack.DistributionDomainName = d1234567890abc.cloudfront.net
WildfireFrontendStack.WebsiteURL = https://wildfire.brazilflyinglabs.org
```

## Step 4: Verification

### 4.1 Verify S3 Bucket
```bash
aws s3 ls | grep wildfire-frontend
```

### 4.2 Verify CloudFront Distribution
```bash
aws cloudfront list-distributions --query 'DistributionList.Items[?Comment==`Frontend Distribution`]'
```

### 4.3 Verify SSM Parameters
```bash
aws ssm get-parameter --name /wildfire/frontend/bucket-name
aws ssm get-parameter --name /wildfire/frontend/distribution-id
```

## Step 5: Environment Variables Setup

### 5.1 Create Parameter Store Values

```bash
# API Gateway endpoint (update with your actual endpoint)
aws ssm put-parameter \
  --name "/wildfire/frontend/api-base-url" \
  --value "https://your-api-id.execute-api.us-east-1.amazonaws.com/v1" \
  --type "String" \
  --description "Backend API base URL for frontend"

# S3 bucket for imagery (from existing backend)
aws ssm put-parameter \
  --name "/wildfire/frontend/imagery-bucket" \
  --value "bfl-satellite-imagery-account-id" \
  --type "String" \
  --description "S3 bucket containing satellite imagery"
```

### 5.2 Verify Parameters
```bash
aws ssm get-parameters --names \
  "/wildfire/frontend/api-base-url" \
  "/wildfire/frontend/imagery-bucket" \
  "/wildfire/frontend/bucket-name" \
  "/wildfire/frontend/distribution-id"
```

## Troubleshooting

### Common Issues

**Issue**: CDK deploy fails with VPC not found
**Solution**: Verify VPC ID exists in target region:
```bash
aws ec2 describe-vpcs --vpc-ids vpc-0e21d3f08ee49572b
```

**Issue**: Certificate validation timeout
**Solution**: Ensure DNS is properly configured for domain validation

**Issue**: CloudFront deployment takes too long
**Solution**: CloudFront distributions can take 15-45 minutes to deploy globally

## Success Criteria

- [ ] S3 bucket created and accessible
- [ ] CloudFront distribution deployed and active
- [ ] SSL certificate issued and attached
- [ ] DNS record created (if using Route 53)
- [ ] SSM parameters populated
- [ ] No CDK deployment errors

## Next Steps

Once Phase 1 is complete, proceed to [Phase 2: CI/CD Pipeline Configuration](./phase-2-cicd-pipeline.md).

---

*Estimated Duration: 2-4 hours (including CloudFront propagation time)*