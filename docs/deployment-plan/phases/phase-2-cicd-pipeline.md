# Phase 2: CI/CD Pipeline Configuration

## Overview

This phase establishes automated deployment pipeline for the frontend, enabling push-to-deploy functionality while integrating with the existing AWS infrastructure. We'll configure GitHub Actions for build and deployment automation.

## Prerequisites

Before starting this phase, ensure:
- [ ] Phase 1 (CDK Infrastructure) completed successfully
- [ ] Frontend S3 bucket and CloudFront distribution are active
- [ ] GitHub repository access configured
- [ ] AWS IAM permissions for deployment configured

## Step 1: AWS IAM Configuration

### 1.1 Create Deployment Role

Create an IAM role specifically for GitHub Actions deployment:

**File**: `bfl-backend/cdk/lib/deployment-role-stack.ts`

```typescript
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export class DeploymentRoleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // GitHub OIDC Provider (if not already exists)
    const gitHubProvider = new iam.OpenIdConnectProvider(this, 'GitHubProvider', {
      url: 'https://token.actions.githubusercontent.com',
      clientIds: ['sts.amazonaws.com'],
      thumbprints: ['6938fd4d98bab03faadb97b34396831e3780aea1'],
    });

    // Deployment role for GitHub Actions
    const deploymentRole = new iam.Role(this, 'GitHubActionsDeploymentRole', {
      roleName: 'WildfireGitHubActionsRole',
      assumedBy: new iam.WebIdentityPrincipal(
        gitHubProvider.openIdConnectProviderArn,
        {
          StringEquals: {
            'token.actions.githubusercontent.com:aud': 'sts.amazonaws.com',
          },
          StringLike: {
            'token.actions.githubusercontent.com:sub': 'repo:boonevoyage/wildfire-assessment:*',
          },
        }
      ),
    });

    // Permissions for S3 deployment
    deploymentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          's3:PutObject',
          's3:PutObjectAcl',
          's3:GetObject',
          's3:DeleteObject',
          's3:ListBucket',
        ],
        resources: [
          `arn:aws:s3:::wildfire-frontend-${this.account}-${this.region}`,
          `arn:aws:s3:::wildfire-frontend-${this.account}-${this.region}/*`,
        ],
      })
    );

    // Permissions for CloudFront invalidation
    deploymentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['cloudfront:CreateInvalidation'],
        resources: ['*'], // CloudFront invalidations require wildcard
      })
    );

    // Permissions to read SSM parameters
    deploymentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['ssm:GetParameter', 'ssm:GetParameters'],
        resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/wildfire/frontend/*`],
      })
    );

    // Store role ARN in SSM for GitHub Actions
    new ssm.StringParameter(this, 'DeploymentRoleArn', {
      parameterName: '/wildfire/frontend/deployment-role-arn',
      stringValue: deploymentRole.roleArn,
      description: 'IAM role ARN for GitHub Actions deployment',
    });

    // Output
    new cdk.CfnOutput(this, 'DeploymentRoleArn', {
      value: deploymentRole.roleArn,
      description: 'GitHub Actions deployment role ARN',
    });
  }
}
```

### 1.2 Deploy Deployment Role

```bash
cd bfl-backend/cdk
cdk deploy WildfireDeploymentRoleStack
```

## Step 2: Frontend Code Configuration

### 2.1 Update Next.js Configuration

**File**: `bfl-frontend/next.config.ts`

```typescript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable static export for S3 hosting
  output: 'export',
  
  // Add trailing slashes for S3 compatibility
  trailingSlash: true,
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_IMAGERY_BUCKET: process.env.NEXT_PUBLIC_IMAGERY_BUCKET,
    NEXT_PUBLIC_CDN_URL: process.env.NEXT_PUBLIC_CDN_URL,
  },
  
  // Asset prefix for CloudFront
  assetPrefix: process.env.NODE_ENV === 'production' ? process.env.NEXT_PUBLIC_CDN_URL : '',
};

export default nextConfig;
```

### 2.2 Update Package.json Scripts

**File**: `bfl-frontend/package.json`

```json
{
  "scripts": {
    "dev": "next dev --turbopack",
    "build": "next build",
    "build:export": "next build && next export",
    "start": "next start",
    "lint": "next lint",
    "deploy:build": "npm run build:export"
  }
}
```

### 2.3 Create Environment Variables Template

**File**: `bfl-frontend/.env.example`

```bash
# Production API endpoint
NEXT_PUBLIC_API_BASE_URL=https://your-api-gateway.execute-api.us-east-1.amazonaws.com/v1

# S3 bucket for satellite imagery
NEXT_PUBLIC_IMAGERY_BUCKET=bfl-satellite-imagery-account-id

# CloudFront distribution URL
NEXT_PUBLIC_CDN_URL=https://your-distribution.cloudfront.net

# Optional: Google Earth Engine settings
NEXT_PUBLIC_GEE_CLIENT_ID=your-gee-client-id
```

## Step 3: GitHub Actions Workflow

### 3.1 Create Workflow Directory

```bash
mkdir -p .github/workflows
```

### 3.2 Create Deployment Workflow

**File**: `.github/workflows/deploy-frontend.yml`

```yaml
name: Deploy Frontend to AWS

on:
  push:
    branches: [main, updates]
    paths: ['bfl-frontend/**']
  pull_request:
    branches: [main]
    paths: ['bfl-frontend/**']
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  NODE_VERSION: 18

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    # Only deploy on push to main/updates, not PRs
    if: github.event_name != 'pull_request'
    
    permissions:
      id-token: write
      contents: read
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: bfl-frontend/package-lock.json
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOYMENT_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Get deployment parameters
        id: params
        run: |
          BUCKET_NAME=$(aws ssm get-parameter --name "/wildfire/frontend/bucket-name" --query "Parameter.Value" --output text)
          DISTRIBUTION_ID=$(aws ssm get-parameter --name "/wildfire/frontend/distribution-id" --query "Parameter.Value" --output text)
          API_BASE_URL=$(aws ssm get-parameter --name "/wildfire/frontend/api-base-url" --query "Parameter.Value" --output text)
          IMAGERY_BUCKET=$(aws ssm get-parameter --name "/wildfire/frontend/imagery-bucket" --query "Parameter.Value" --output text)
          CDN_URL=$(aws cloudfront get-distribution --id $DISTRIBUTION_ID --query "Distribution.DomainName" --output text)
          
          echo "bucket-name=$BUCKET_NAME" >> $GITHUB_OUTPUT
          echo "distribution-id=$DISTRIBUTION_ID" >> $GITHUB_OUTPUT
          echo "api-base-url=$API_BASE_URL" >> $GITHUB_OUTPUT
          echo "imagery-bucket=$IMAGERY_BUCKET" >> $GITHUB_OUTPUT
          echo "cdn-url=https://$CDN_URL" >> $GITHUB_OUTPUT
      
      - name: Install dependencies
        run: |
          cd bfl-frontend
          npm ci
      
      - name: Run linting
        run: |
          cd bfl-frontend
          npm run lint
      
      - name: Build application
        run: |
          cd bfl-frontend
          npm run build
        env:
          NEXT_PUBLIC_API_BASE_URL: ${{ steps.params.outputs.api-base-url }}
          NEXT_PUBLIC_IMAGERY_BUCKET: ${{ steps.params.outputs.imagery-bucket }}
          NEXT_PUBLIC_CDN_URL: ${{ steps.params.outputs.cdn-url }}
          NODE_ENV: production
      
      - name: Deploy to S3
        run: |
          cd bfl-frontend
          aws s3 sync ./out/ s3://${{ steps.params.outputs.bucket-name }}/ \
            --delete \
            --cache-control "public,max-age=31536000,immutable" \
            --exclude "*.html" \
            --exclude "*.json"
          
          # HTML and JSON files with shorter cache
          aws s3 sync ./out/ s3://${{ steps.params.outputs.bucket-name }}/ \
            --cache-control "public,max-age=0,s-maxage=31536000" \
            --exclude "*" \
            --include "*.html" \
            --include "*.json"
      
      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ steps.params.outputs.distribution-id }} \
            --paths "/*"
      
      - name: Deployment notification
        if: success()
        run: |
          echo "✅ Frontend deployed successfully!"
          echo "🌐 URL: https://${{ steps.params.outputs.cdn-url }}"
          echo "📦 S3 Bucket: ${{ steps.params.outputs.bucket-name }}"
          echo "🚀 CloudFront Distribution: ${{ steps.params.outputs.distribution-id }}"

  test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: bfl-frontend/package-lock.json
      
      - name: Install dependencies
        run: |
          cd bfl-frontend
          npm ci
      
      - name: Run linting
        run: |
          cd bfl-frontend
          npm run lint
      
      - name: Build test
        run: |
          cd bfl-frontend
          npm run build
        env:
          NEXT_PUBLIC_API_BASE_URL: "https://api.example.com"
          NEXT_PUBLIC_IMAGERY_BUCKET: "test-bucket"
          NEXT_PUBLIC_CDN_URL: "https://test.cloudfront.net"
```

## Step 4: GitHub Repository Configuration

### 4.1 Add Repository Secrets

In your GitHub repository settings, add these secrets:

1. Go to Repository Settings → Secrets and variables → Actions
2. Add the following secrets:

**Required Secrets:**
- `AWS_DEPLOYMENT_ROLE_ARN`: Get from CDK output or SSM parameter

```bash
# Get the deployment role ARN
aws ssm get-parameter --name "/wildfire/frontend/deployment-role-arn" --query "Parameter.Value" --output text
```

### 4.2 Repository Settings

1. **Branch Protection**: Configure branch protection rules for main branch
2. **Required Status Checks**: Make the test job required before merging
3. **Auto-merge**: Enable auto-merge for dependency updates

## Step 5: Local Testing

### 5.1 Test Build Process Locally

```bash
cd bfl-frontend

# Install dependencies
npm ci

# Set environment variables
export NEXT_PUBLIC_API_BASE_URL="https://your-api-gateway.amazonaws.com/v1"
export NEXT_PUBLIC_IMAGERY_BUCKET="bfl-satellite-imagery-account-id"
export NEXT_PUBLIC_CDN_URL="https://your-distribution.cloudfront.net"

# Test build
npm run build

# Verify output directory
ls -la out/
```

### 5.2 Test S3 Sync (Optional)

```bash
# Test S3 sync without deployment
aws s3 sync ./out/ s3://your-test-bucket/ --dryrun
```

## Step 6: First Deployment

### 6.1 Trigger Initial Deployment

```bash
# Commit and push changes
git add .
git commit -m "Configure CI/CD pipeline for frontend deployment"
git push origin updates
```

### 6.2 Monitor Deployment

1. Go to GitHub Actions tab in your repository
2. Monitor the "Deploy Frontend to AWS" workflow
3. Check for any errors in the deployment process

### 6.3 Verify Deployment

```bash
# Check S3 bucket contents
aws s3 ls s3://wildfire-frontend-account-region/ --recursive

# Check CloudFront invalidation status
aws cloudfront list-invalidations --distribution-id YOUR_DISTRIBUTION_ID
```

## Troubleshooting

### Common Issues

**Issue**: GitHub Actions role assumption fails
**Solution**: Verify the role trust policy and repository name in the condition

**Issue**: S3 sync permission denied
**Solution**: Check IAM policy allows s3:PutObject and s3:DeleteObject

**Issue**: CloudFront invalidation fails
**Solution**: Ensure cloudfront:CreateInvalidation permission is granted

**Issue**: Build fails with missing environment variables
**Solution**: Verify all required NEXT_PUBLIC_* variables are set in the workflow

### Debug Commands

```bash
# Test AWS credentials
aws sts get-caller-identity

# Verify S3 bucket access
aws s3 ls s3://your-bucket-name/

# Check CloudFront distribution status
aws cloudfront get-distribution --id YOUR_DISTRIBUTION_ID
```

## Success Criteria

- [ ] GitHub Actions workflow runs successfully
- [ ] Frontend builds without errors
- [ ] Static files deploy to S3 bucket
- [ ] CloudFront cache invalidation completes
- [ ] Website accessible via CloudFront URL
- [ ] All environment variables properly configured

## Next Steps

Once Phase 2 is complete, proceed to [Phase 3: Integration & Testing](./phase-3-integration-testing.md).

---

*Estimated Duration: 4-6 hours (including testing and troubleshooting)*