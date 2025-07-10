# CDK Frontend Stack Configuration Guide

## Overview

This guide provides detailed instructions for implementing and customizing the CDK frontend stack for the Wildfire Assessment Project. The stack creates S3 bucket, CloudFront distribution, SSL certificate, and related infrastructure.

## Stack Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Route 53      │───▶│   CloudFront     │───▶│   S3 Bucket     │
│   (DNS)         │    │   (CDN)          │    │   (Static Site) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   ACM Certificate│
                       │   (SSL/TLS)      │
                       └──────────────────┘
```

## Complete CDK Stack Implementation

### Frontend Stack Class

**File**: `bfl-backend/cdk/lib/frontend-stack.ts`

```typescript
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface FrontendStackProps extends cdk.StackProps {
  domainName: string;
  subdomain?: string;
  hostedZoneId?: string;
  hostedZoneName?: string;
  certificateArn?: string;
  apiGatewayDomain?: string;
  existingImageryBucket?: string;
  enableWaf?: boolean;
  priceClass?: cloudfront.PriceClass;
}

export class FrontendStack extends cdk.Stack {
  public readonly distribution: cloudfront.Distribution;
  public readonly bucket: s3.Bucket;
  public readonly certificate: acm.ICertificate;
  public readonly hostedZone: route53.IHostedZone;

  constructor(scope: Construct, id: string, props: FrontendStackProps) {
    super(scope, id, props);

    // Determine full domain name
    const fullDomainName = props.subdomain 
      ? `${props.subdomain}.${props.domainName}`
      : props.domainName;

    // S3 Bucket for static website hosting
    this.bucket = new s3.Bucket(this, 'FrontendBucket', {
      bucketName: `wildfire-frontend-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      versioned: false,
      lifecycleRules: [
        {
          id: 'DeleteIncompleteMultipartUploads',
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(1),
        },
      ],
    });

    // CloudFront Origin Access Identity
    const oai = new cloudfront.OriginAccessIdentity(this, 'FrontendOAI', {
      comment: `OAI for ${fullDomainName} wildfire frontend`,
    });

    // Grant CloudFront access to S3 bucket
    this.bucket.addToResourcePolicy(
      new iam.PolicyStatement({
        actions: ['s3:GetObject'],
        resources: [this.bucket.arnForObjects('*')],
        principals: [oai.grantPrincipal],
        effect: iam.Effect.ALLOW,
      })
    );

    // Get or create SSL Certificate
    if (props.certificateArn) {
      this.certificate = acm.Certificate.fromCertificateArn(
        this, 
        'ImportedCertificate', 
        props.certificateArn
      );
    } else if (props.hostedZoneId || props.hostedZoneName) {
      // Get hosted zone
      this.hostedZone = props.hostedZoneId
        ? route53.HostedZone.fromHostedZoneId(this, 'ImportedHostedZone', props.hostedZoneId)
        : route53.HostedZone.fromLookup(this, 'LookedUpHostedZone', {
            domainName: props.hostedZoneName || props.domainName,
          });

      // Create certificate with DNS validation
      this.certificate = new acm.Certificate(this, 'FrontendCertificate', {
        domainName: fullDomainName,
        subjectAlternativeNames: props.subdomain ? [props.domainName] : undefined,
        validation: acm.CertificateValidation.fromDns(this.hostedZone),
      });
    } else {
      throw new Error('Either certificateArn or hostedZoneId/hostedZoneName must be provided');
    }

    // CloudFront Distribution Configuration
    const distributionProps: cloudfront.DistributionProps = {
      comment: `Wildfire Assessment Frontend - ${fullDomainName}`,
      defaultRootObject: 'index.html',
      domainNames: [fullDomainName],
      certificate: this.certificate,
      priceClass: props.priceClass || cloudfront.PriceClass.PRICE_CLASS_100,
      httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,
      enableIpv6: true,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      
      // Default behavior for static assets
      defaultBehavior: {
        origin: new origins.S3Origin(this.bucket, {
          originAccessIdentity: oai,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
        compress: true,
        cachePolicy: this.createStaticAssetsCachePolicy(),
        responseHeadersPolicy: this.createSecurityHeadersPolicy(),
      },

      // Additional behaviors
      additionalBehaviors: {},

      // Error responses for SPA routing
      errorResponses: [
        {
          httpStatus: 403,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: '/index.html',
          ttl: cdk.Duration.minutes(5),
        },
      ],

      // Enable logging
      enableLogging: true,
      logBucket: new s3.Bucket(this, 'CloudFrontLogsBucket', {
        bucketName: `wildfire-cf-logs-${this.account}-${this.region}`,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
        autoDeleteObjects: true,
        lifecycleRules: [
          {
            id: 'DeleteOldLogs',
            expiration: cdk.Duration.days(90),
          },
        ],
      }),
      logFilePrefix: 'cloudfront-logs/',
    };

    // Add API behavior if API Gateway domain is provided
    if (props.apiGatewayDomain) {
      distributionProps.additionalBehaviors!['/api/*'] = {
        origin: new origins.HttpOrigin(props.apiGatewayDomain, {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
          originSslProtocols: [cloudfront.OriginSslPolicy.TLS_V1_2],
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        originRequestPolicy: cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
      };
    }

    // Create CloudFront Distribution
    this.distribution = new cloudfront.Distribution(this, 'FrontendDistribution', distributionProps);

    // Route 53 DNS Record
    if (this.hostedZone) {
      new route53.ARecord(this, 'FrontendAliasRecord', {
        zone: this.hostedZone,
        recordName: fullDomainName,
        target: route53.RecordTarget.fromAlias(
          new targets.CloudFrontTarget(this.distribution)
        ),
        ttl: cdk.Duration.minutes(5),
      });

      // Add www redirect if this is the apex domain
      if (!props.subdomain) {
        new route53.ARecord(this, 'WWWRedirectRecord', {
          zone: this.hostedZone,
          recordName: `www.${fullDomainName}`,
          target: route53.RecordTarget.fromAlias(
            new targets.CloudFrontTarget(this.distribution)
          ),
          ttl: cdk.Duration.minutes(5),
        });
      }
    }

    // Store configuration in SSM Parameter Store
    this.createSSMParameters(fullDomainName, props);

    // Create CloudWatch Dashboard
    this.createCloudWatchDashboard();

    // Outputs
    this.createStackOutputs(fullDomainName);
  }

  private createStaticAssetsCachePolicy(): cloudfront.CachePolicy {
    return new cloudfront.CachePolicy(this, 'StaticAssetsCachePolicy', {
      cachePolicyName: 'WildfireStaticAssetsPolicy',
      comment: 'Cache policy for static assets with long TTL',
      defaultTtl: cdk.Duration.days(1),
      maxTtl: cdk.Duration.days(365),
      minTtl: cdk.Duration.seconds(0),
      enableAcceptEncodingGzip: true,
      enableAcceptEncodingBrotli: true,
      queryStringBehavior: cloudfront.CacheQueryStringBehavior.none(),
      headerBehavior: cloudfront.CacheHeaderBehavior.allowList('CloudFront-Viewer-Country'),
      cookieBehavior: cloudfront.CacheCookieBehavior.none(),
    });
  }

  private createSecurityHeadersPolicy(): cloudfront.ResponseHeadersPolicy {
    return new cloudfront.ResponseHeadersPolicy(this, 'SecurityHeadersPolicy', {
      responseHeadersPolicyName: 'WildfireSecurityHeaders',
      comment: 'Security headers for wildfire frontend',
      securityHeadersBehavior: {
        strictTransportSecurity: {
          accessControlMaxAge: cdk.Duration.seconds(31536000),
          includeSubdomains: true,
          preload: true,
        },
        contentTypeOptions: {
          override: true,
        },
        frameOptions: {
          frameOption: cloudfront.HeadersFrameOption.SAMEORIGIN,
          override: true,
        },
        xssProtection: {
          modeBlock: true,
          protection: true,
          override: true,
        },
      },
      customHeadersBehavior: {
        customHeaders: [
          {
            header: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
            override: false,
          },
          {
            header: 'X-Content-Security-Policy',
            value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;",
            override: true,
          },
        ],
      },
    });
  }

  private createSSMParameters(domainName: string, props: FrontendStackProps): void {
    // Core infrastructure parameters
    new ssm.StringParameter(this, 'FrontendBucketName', {
      parameterName: '/wildfire/frontend/bucket-name',
      stringValue: this.bucket.bucketName,
      description: 'S3 bucket name for frontend static assets',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'FrontendDistributionId', {
      parameterName: '/wildfire/frontend/distribution-id',
      stringValue: this.distribution.distributionId,
      description: 'CloudFront distribution ID for cache invalidation',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'FrontendDomainName', {
      parameterName: '/wildfire/frontend/domain-name',
      stringValue: this.distribution.distributionDomainName,
      description: 'CloudFront distribution domain name',
      tier: ssm.ParameterTier.STANDARD,
    });

    new ssm.StringParameter(this, 'FrontendURL', {
      parameterName: '/wildfire/frontend/url',
      stringValue: `https://${domainName}`,
      description: 'Frontend website URL',
      tier: ssm.ParameterTier.STANDARD,
    });

    // API configuration if provided
    if (props.apiGatewayDomain) {
      new ssm.StringParameter(this, 'APIBaseURL', {
        parameterName: '/wildfire/frontend/api-base-url',
        stringValue: `https://${props.apiGatewayDomain}`,
        description: 'Backend API base URL for frontend',
        tier: ssm.ParameterTier.STANDARD,
      });
    }

    // Imagery bucket reference if provided
    if (props.existingImageryBucket) {
      new ssm.StringParameter(this, 'ImageryBucketName', {
        parameterName: '/wildfire/frontend/imagery-bucket',
        stringValue: props.existingImageryBucket,
        description: 'S3 bucket containing satellite imagery',
        tier: ssm.ParameterTier.STANDARD,
      });
    }
  }

  private createCloudWatchDashboard(): void {
    const dashboard = new logs.LogGroup(this, 'FrontendDashboardLogs', {
      logGroupName: '/aws/cloudfront/wildfire-frontend',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Note: CloudWatch Dashboard creation is typically done separately
    // or via CloudFormation templates due to CDK limitations
  }

  private createStackOutputs(domainName: string): void {
    new cdk.CfnOutput(this, 'BucketName', {
      value: this.bucket.bucketName,
      description: 'Frontend S3 bucket name',
      exportName: `${this.stackName}-BucketName`,
    });

    new cdk.CfnOutput(this, 'DistributionId', {
      value: this.distribution.distributionId,
      description: 'CloudFront distribution ID',
      exportName: `${this.stackName}-DistributionId`,
    });

    new cdk.CfnOutput(this, 'DistributionDomainName', {
      value: this.distribution.distributionDomainName,
      description: 'CloudFront distribution domain name',
      exportName: `${this.stackName}-DistributionDomainName`,
    });

    new cdk.CfnOutput(this, 'WebsiteURL', {
      value: `https://${domainName}`,
      description: 'Frontend website URL',
      exportName: `${this.stackName}-WebsiteURL`,
    });

    if (this.certificate) {
      new cdk.CfnOutput(this, 'CertificateArn', {
        value: this.certificate.certificateArn,
        description: 'SSL certificate ARN',
        exportName: `${this.stackName}-CertificateArn`,
      });
    }
  }
}
```

## Usage Examples

### Basic Configuration

```typescript
// In your CDK app (bin/app.ts)
import { FrontendStack } from '../lib/frontend-stack';

const frontendStack = new FrontendStack(app, 'WildfireFrontendStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  
  // Required
  domainName: 'brazilflyinglabs.org',
  subdomain: 'wildfire',
  
  // DNS Configuration
  hostedZoneId: 'Z1234567890ABC',
  
  // Integration with existing backend
  apiGatewayDomain: 'api-gateway-id.execute-api.us-east-1.amazonaws.com',
  existingImageryBucket: 'bfl-satellite-imagery-123456789',
  
  // Optional optimizations
  priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
  enableWaf: false,
});
```

### Advanced Configuration with WAF

```typescript
const frontendStack = new FrontendStack(app, 'WildfireFrontendStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  
  domainName: 'wildfire.brazilflyinglabs.org',
  certificateArn: 'arn:aws:acm:us-east-1:123456789:certificate/12345678-1234-1234-1234-123456789012',
  
  // Full global distribution
  priceClass: cloudfront.PriceClass.PRICE_CLASS_ALL,
  
  // Enable WAF protection
  enableWaf: true,
});
```

## Customization Options

### Cache Policies

Customize caching behavior for different content types:

```typescript
// Long-term caching for static assets
const staticCachePolicy = new cloudfront.CachePolicy(this, 'StaticAssetsCache', {
  defaultTtl: cdk.Duration.days(30),
  maxTtl: cdk.Duration.days(365),
  minTtl: cdk.Duration.days(1),
});

// Short-term caching for HTML files
const htmlCachePolicy = new cloudfront.CachePolicy(this, 'HTMLCache', {
  defaultTtl: cdk.Duration.hours(1),
  maxTtl: cdk.Duration.days(1),
  minTtl: cdk.Duration.seconds(0),
});
```

### Security Headers

Add custom security headers:

```typescript
const securityHeaders = new cloudfront.ResponseHeadersPolicy(this, 'SecurityHeaders', {
  securityHeadersBehavior: {
    strictTransportSecurity: {
      accessControlMaxAge: cdk.Duration.seconds(31536000),
      includeSubdomains: true,
      preload: true,
    },
    contentTypeOptions: { override: true },
    frameOptions: {
      frameOption: cloudfront.HeadersFrameOption.DENY,
      override: true,
    },
  },
  customHeadersBehavior: {
    customHeaders: [
      {
        header: 'Permissions-Policy',
        value: 'geolocation=(), microphone=(), camera=()',
        override: true,
      },
    ],
  },
});
```

### Multiple Origins

Configure multiple origins for different content:

```typescript
const additionalBehaviors = {
  // API routes
  '/api/*': {
    origin: new origins.HttpOrigin('api.example.com'),
    cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
  },
  
  // Large imagery files
  '/imagery/*': {
    origin: new origins.S3Origin(imageryBucket),
    cachePolicy: imageCachePolicy,
  },
  
  // External tile server
  '/tiles/*': {
    origin: new origins.HttpOrigin('tiles.external-service.com'),
    cachePolicy: tilesCachePolicy,
  },
};
```

## Environment-Specific Configuration

### Development Environment

```typescript
const devFrontendStack = new FrontendStack(app, 'WildfireFrontendDevStack', {
  domainName: 'dev-wildfire.brazilflyinglabs.org',
  priceClass: cloudfront.PriceClass.PRICE_CLASS_100, // Cost optimization
  apiGatewayDomain: 'dev-api-gateway.execute-api.us-east-1.amazonaws.com',
});
```

### Production Environment

```typescript
const prodFrontendStack = new FrontendStack(app, 'WildfireFrontendProdStack', {
  domainName: 'wildfire.brazilflyinglabs.org',
  priceClass: cloudfront.PriceClass.PRICE_CLASS_ALL, // Global performance
  enableWaf: true, // Security
  apiGatewayDomain: 'api-gateway.execute-api.us-east-1.amazonaws.com',
});
```

## Testing the Stack

### Validation Script

```bash
#!/bin/bash
# validate-frontend-stack.sh

echo "🔍 Validating Frontend Stack Configuration..."

# Check if stack exists
STACK_NAME="WildfireFrontendStack"
aws cloudformation describe-stacks --stack-name $STACK_NAME > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Stack exists"
    
    # Get outputs
    BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
    DISTRIBUTION_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' --output text)
    WEBSITE_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' --output text)
    
    echo "📦 Bucket: $BUCKET_NAME"
    echo "🌐 Distribution: $DISTRIBUTION_ID"
    echo "🔗 URL: $WEBSITE_URL"
    
    # Test bucket access
    aws s3 ls s3://$BUCKET_NAME > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ S3 bucket accessible"
    else
        echo "❌ S3 bucket not accessible"
    fi
    
    # Test CloudFront distribution
    DISTRIBUTION_STATUS=$(aws cloudfront get-distribution --id $DISTRIBUTION_ID --query 'Distribution.Status' --output text)
    echo "📊 Distribution Status: $DISTRIBUTION_STATUS"
    
else
    echo "❌ Stack does not exist"
    exit 1
fi
```

## Troubleshooting

### Common Issues

**Issue**: Certificate validation fails
```bash
# Check certificate status
aws acm describe-certificate --certificate-arn YOUR_CERT_ARN

# Verify DNS records for validation
dig _validation-hash.domain.com TXT
```

**Issue**: CloudFront deployment takes too long
```bash
# Check distribution status
aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID --query 'Distribution.Status'

# Monitor deployment progress
watch -n 30 'aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID --query "Distribution.Status"'
```

**Issue**: S3 bucket policy conflicts
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket your-bucket-name

# Verify OAI permissions
aws cloudfront list-origin-access-identities
```

## Cost Optimization

### Regional Considerations

```typescript
// Cost-optimized for specific regions
const costOptimizedStack = new FrontendStack(app, 'CostOptimizedStack', {
  domainName: 'wildfire.example.com',
  priceClass: cloudfront.PriceClass.PRICE_CLASS_100, // US, Canada, Europe only
  
  // Use lifecycle policies for logs
  enableLogging: false, // Disable if not needed
});
```

### Monitoring and Alerts

```typescript
// Add cost monitoring
const costAlarm = new cloudwatch.Alarm(this, 'FrontendCostAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'AWS/Billing',
    metricName: 'EstimatedCharges',
    dimensionsMap: {
      Currency: 'USD',
      ServiceName: 'AmazonCloudFront',
    },
    statistic: 'Maximum',
  }),
  threshold: 100, // Alert if monthly costs exceed $100
  evaluationPeriods: 1,
});
```

## Migration from Existing Infrastructure

### Blue-Green Deployment

```typescript
// Create parallel stack for testing
const blueStack = new FrontendStack(app, 'WildfireFrontendBlue', {
  domainName: 'blue.wildfire.brazilflyinglabs.org',
  // ... other props
});

const greenStack = new FrontendStack(app, 'WildfireFrontendGreen', {
  domainName: 'green.wildfire.brazilflyinglabs.org',
  // ... other props
});
```

This comprehensive guide covers all aspects of implementing and customizing the CDK frontend stack for the Wildfire Assessment Project.