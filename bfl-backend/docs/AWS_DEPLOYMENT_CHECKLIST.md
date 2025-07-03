# AWS Deployment Checklist for BOIFL System

## Client Information Required

### **1. AWS Account Details**
- [ ] AWS Account ID
- [ ] Primary deployment region (recommend: `us-east-1` or `us-west-2`)
- [ ] Secondary region (optional, for disaster recovery)
- [ ] AWS Organization ID (if applicable)

### **2. Access & Permissions**
- [ ] IAM user/role with deployment permissions:
  - [ ] Administrator access OR specific permissions for:
    - CDK Bootstrap permissions
    - S3, Batch, Step Functions, Lambda, VPC, ECR, IAM, CloudWatch
- [ ] AWS CLI configured locally with deployment credentials
- [ ] Confirm CDK bootstrap status in target region

### **3. Network Configuration**
- [ ] **CRITICAL**: Update hardcoded VPC/Subnet IDs in `bin/app.ts`:
  - Current: `vpc-0e21d3f08ee49572b` 
  - Current subnets: `subnet-0ea02d54ffe1b12b4`, `subnet-0114ece9f119f3ae5`
- [ ] VPC with public subnets (for Fargate public IP assignment)
- [ ] Internet Gateway attached to VPC
- [ ] Route tables configured for internet access

### **4. Domain & SSL**
- [ ] Domain name for frontend deployment
- [ ] SSL certificate (AWS Certificate Manager or external)
- [ ] DNS management access (Route 53 or external DNS provider)

### **5. Security & Secrets**
- [ ] Google Earth Engine service account JSON credentials
- [ ] Decide on secrets management approach:
  - [ ] AWS Secrets Manager (recommended)
  - [ ] Environment variables
  - [ ] AWS Systems Manager Parameter Store

---

## Pre-Deployment Setup Tasks

### **Backend Infrastructure (Priority 1)**
- [ ] **Update CDK configuration**:
  - [ ] Replace hardcoded VPC/subnet IDs in `bin/app.ts`
  - [ ] Configure bucket name prefix
  - [ ] Set deployment region
- [ ] **Security hardening**:
  - [ ] Move GEE credentials to AWS Secrets Manager
  - [ ] Update S3 bucket policy (remove public access, implement CloudFront)
  - [ ] Review IAM roles for least privilege
- [ ] **CDK Bootstrap**:
  ```bash
  cd bfl-backend/cdk
  npm install
  cdk bootstrap aws://ACCOUNT-ID/REGION
  ```

### **Frontend Configuration (Priority 2)**
- [ ] **Environment variables setup**:
  - [ ] `NEXT_PUBLIC_API_BASE` - Backend API endpoint
  - [ ] `NEXT_PUBLIC_CDN` - CloudFront distribution URL
  - [ ] `NEXT_PUBLIC_S3_BUCKET` - S3 bucket name
- [ ] **Build configuration**:
  - [ ] Update CORS origins in backend stack
  - [ ] Configure deployment target (Vercel/Netlify/AWS Amplify)

### **Google Earth Engine Setup (Priority 3)**
- [ ] **Service account verification**:
  - [ ] Confirm GEE service account has proper permissions
  - [ ] Test authentication outside of application
  - [ ] Store credentials securely in AWS Secrets Manager

---

## Deployment Sequence

### **Phase 1: Backend Infrastructure**
1. **Deploy CDK Stack**:
   ```bash
   cd bfl-backend/cdk
   cdk diff  # Review changes
   cdk deploy
   ```
2. **Verify resources**:
   - [ ] S3 bucket created
   - [ ] Batch compute environment active
   - [ ] Step Functions state machine deployed
   - [ ] Docker image built and pushed to ECR

### **Phase 2: Security Configuration**
1. **Configure secrets**:
   - [ ] Upload GEE credentials to Secrets Manager
   - [ ] Update Lambda environment variables
   - [ ] Test secret retrieval
2. **Network verification**:
   - [ ] VPC endpoints accessible
   - [ ] Security groups allow required traffic
   - [ ] Fargate tasks can reach internet

### **Phase 3: Frontend Deployment**
1. **Configure environment**:
   - [ ] Set all required environment variables
   - [ ] Update API endpoints
   - [ ] Configure CDN/CloudFront
2. **Deploy frontend**:
   - [ ] Build and test locally
   - [ ] Deploy to hosting platform
   - [ ] Verify CORS configuration

### **Phase 4: Testing & Validation**
- [ ] **Functional testing**:
  - [ ] Submit test batch job
  - [ ] Verify image processing pipeline
  - [ ] Test frontend satellite image display
- [ ] **Performance testing**:
  - [ ] Monitor CloudWatch metrics
  - [ ] Verify Step Functions execution
  - [ ] Test concurrent job processing
- [ ] **Security validation**:
  - [ ] Confirm no public access to sensitive data
  - [ ] Verify IAM roles work correctly
  - [ ] Test authentication flow

---

## Cost Estimation

### **Monthly Operating Costs (Estimate)**
- [ ] **Compute**: $50-200/month (Fargate Spot + Step Functions)
- [ ] **Storage**: $20-100/month (S3 storage for imagery)
- [ ] **Data Transfer**: $10-50/month (CloudFront + S3 egress)
- [ ] **Other Services**: $10-30/month (Lambda, Secrets Manager, CloudWatch)

**Total Estimated**: $90-380/month depending on usage

---

## Critical Configuration Updates Needed

### **🚨 Must Fix Before Deployment**
1. **Replace hardcoded VPC/subnet IDs** in `bfl-backend/cdk/bin/app.ts:9-13`
2. **Remove placeholder domain** in CORS configuration
3. **Configure GEE credentials storage** (move from filesystem to Secrets Manager)
4. **Update S3 bucket security** (remove public access, implement proper access controls)

### **⚠️ Recommended Before Deployment**
1. **Add monitoring/alerting** for batch job failures
2. **Implement proper error handling** in Step Functions
3. **Configure backup strategy** for processed imagery
4. **Set up log aggregation** for troubleshooting

---

## Quick Commands Reference

### **CDK Commands**
```bash
# Install dependencies
cd bfl-backend/cdk && npm install

# Bootstrap CDK (one-time per region)
cdk bootstrap aws://ACCOUNT-ID/REGION

# Review changes before deployment
cdk diff

# Deploy the stack
cdk deploy

# Destroy the stack (if needed)
cdk destroy
```

### **AWS CLI Commands for Setup**
```bash
# Configure AWS CLI
aws configure

# Verify account access
aws sts get-caller-identity

# List available VPCs
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,Tags[?Key==`Name`].Value|[0]]' --output table

# List subnets in a VPC
aws ec2 describe-subnets --filters "Name=vpc-id,Values=VPC-ID" --query 'Subnets[*].[SubnetId,AvailabilityZone,MapPublicIpOnLaunch]' --output table
```

### **Environment Variables Template**
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_BASE=https://your-api-gateway.execute-api.region.amazonaws.com/v1
NEXT_PUBLIC_CDN=https://your-cloudfront-distribution.cloudfront.net
NEXT_PUBLIC_S3_BUCKET=bfl-satellite-imagery-ACCOUNT-ID

# Backend (AWS Secrets Manager)
EE_CREDENTIALS={"type": "service_account", "project_id": "...", ...}
```

---

## Troubleshooting Common Issues

### **CDK Bootstrap Failures**
- Ensure AWS CLI is configured with proper permissions
- Check if CDK toolkit stack already exists in the region
- Verify account has necessary quotas for CloudFormation stacks

### **Batch Job Failures**
- Check CloudWatch logs for container errors
- Verify VPC endpoints are accessible
- Ensure Docker image builds successfully locally

### **Frontend CORS Errors**
- Update S3 bucket CORS configuration
- Verify API Gateway CORS settings
- Check environment variables match deployed resources

### **GEE Authentication Issues**
- Verify service account has Earth Engine permissions
- Check credentials format in Secrets Manager
- Test authentication with standalone script

---

*Last Updated: 2025-01-03*
*For technical support, refer to the development logs in `/devlog/` directory*