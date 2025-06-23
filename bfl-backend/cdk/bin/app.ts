#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { S2BatchStack } from '../lib/s2-batch-stack';

const app = new cdk.App();

new S2BatchStack(app, 'S2BatchStack', {
  vpcId: 'vpc-0e21d3f08ee49572b',
  subnetIds: [
    'subnet-0ea02d54ffe1b12b4',
    'subnet-0114ece9f119f3ae5',
  ],
  bucketName: 'bfl-satellite-imagery-' + process.env.CDK_DEFAULT_ACCOUNT,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
});
