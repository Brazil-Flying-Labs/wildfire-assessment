# BFL Backend Deployment

## Deployment Process
- [x] Configure Lambda layer (using pre-built layer from lambgeo/titiler-layer)
- [x] Bootstrap CDK in AWS account
- [ ] Deploy the CDK stack
- [ ] Test the deployment

## Progress Log

### 2025-05-20
- Starting deployment of BFL backend
- Verified AWS CLI is installed and configured: aws-cli/2.24.22
- Modified CDK stack to use a pre-built Lambda layer from lambgeo/titiler-layer
- Installed AWS CDK globally
- Successfully bootstrapped CDK in AWS account (aws://339712843779/us-east-1)
- Encountered permission error when trying to use the pre-built Lambda layer:
  ```
  User is not authorized to perform: lambda:GetLayerVersion on resource: arn:aws:lambda:us-east-1:552819999234:layer:TiTilerLayer:1
  ```
- Need to modify our approach to either build our own layer or use a different deployment strategy
