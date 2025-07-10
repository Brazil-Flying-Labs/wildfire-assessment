# AWS Deployment Plan for Wildfire Assessment Project

## Overview

This deployment plan outlines the strategy to migrate the Wildfire Assessment Project frontend from Vercel to AWS, ensuring full consolidation with the existing AWS backend infrastructure while maintaining cost-effectiveness and performance.

## Project Context

- **Frontend**: Next.js 15.2.0 with React 19, satellite imagery visualization
- **Backend**: AWS infrastructure deployed via CDK (S3 Batch, Fargate, Step Functions, Lambda)
- **Current State**: Frontend on Vercel, backend on AWS
- **Goal**: Consolidate everything on AWS for client requirements

## Document Structure

### Phase Documentation
- [Phase 1: CDK Infrastructure Setup](./phases/phase-1-cdk-infrastructure.md)
- [Phase 2: CI/CD Pipeline Configuration](./phases/phase-2-cicd-pipeline.md)
- [Phase 3: Integration & Testing](./phases/phase-3-integration-testing.md)
- [Phase 4: Go-Live & Monitoring](./phases/phase-4-golive-monitoring.md)

### Implementation Guides
- [CDK Frontend Stack Configuration](./guides/cdk-frontend-stack.md)
- [GitHub Actions Setup](./guides/github-actions-setup.md)
- [Environment Variables Management](./guides/environment-variables.md)
- [Domain & SSL Configuration](./guides/domain-ssl-setup.md)
- [CloudFront Optimization](./guides/cloudfront-optimization.md)

### Comparisons & Analysis
- [Platform Comparison: Vercel vs AWS Options](./comparisons/platform-comparison.md)
- [Cost Analysis](./comparisons/cost-analysis.md)
- [Performance Benchmarks](./comparisons/performance-benchmarks.md)

### Examples & Templates
- [CDK Stack Examples](./examples/cdk-examples/)
- [GitHub Actions Workflows](./examples/github-actions/)
- [Configuration Templates](./examples/configs/)

## Recommended Architecture

**S3 + CloudFront Static Hosting**
- Cost-effective (~$45/month)
- Seamless CDK integration
- Optimal for satellite imagery visualization
- Minimal operational overhead

## Quick Start

1. Review [Platform Comparison](./comparisons/platform-comparison.md) to understand the decision rationale
2. Follow [Phase 1: CDK Infrastructure](./phases/phase-1-cdk-infrastructure.md) to set up AWS resources
3. Configure [CI/CD Pipeline](./phases/phase-2-cicd-pipeline.md) for automatic deployments
4. Complete [Integration Testing](./phases/phase-3-integration-testing.md)
5. Execute [Go-Live Plan](./phases/phase-4-golive-monitoring.md)

## Timeline

- **Week 1**: CDK infrastructure deployment
- **Week 2**: CI/CD pipeline setup and testing  
- **Week 3**: Domain configuration and go-live
- **Week 4**: Monitoring and optimization

## Support

For technical questions or issues during implementation:
- Review the relevant phase documentation
- Check the troubleshooting sections in each guide
- Refer to existing `bfl-backend/docs/AWS_DEPLOYMENT_CHECKLIST.md`

---

*Last Updated: 2025-07-10*
*Project: Wildfire Assessment - Brazil Flying Labs*