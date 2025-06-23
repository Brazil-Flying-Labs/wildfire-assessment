import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import * as batch from 'aws-cdk-lib/aws-batch';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as fs from 'fs';
import { Duration, RemovalPolicy, Fn } from 'aws-cdk-lib';
import * as cr from 'aws-cdk-lib/custom-resources';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';

export interface S2BatchStackProps extends cdk.StackProps {
  vpcId: string;
  subnetIds: string[];
  bucketName?: string;
}

export class S2BatchStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: S2BatchStackProps) {
    super(scope, id, props);
    const bucket = new s3.Bucket(this, 'SatelliteImageBucket', {
      bucketName: props.bucketName,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: new s3.BlockPublicAccess({
        blockPublicAcls: false,
        blockPublicPolicy: false,
        ignorePublicAcls: false,
        restrictPublicBuckets: false
      }),
      objectOwnership: s3.ObjectOwnership.OBJECT_WRITER,
      publicReadAccess: true,
      removalPolicy: RemovalPolicy.RETAIN,
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET],
          allowedOrigins: ['http://localhost:3000', 'https://your-production-domain.com'],
          allowedHeaders: ['*'],
        }
      ]
    });
    const bucketPolicy = new s3.BucketPolicy(this, 'BucketPolicy', {
      bucket: bucket,
    });

    bucketPolicy.document.addStatements(
      new iam.PolicyStatement({
        actions: ['s3:GetObject', 's3:ListBucket'],
        resources: [`${bucket.bucketArn}/*`,
          bucket.bucketArn
        ],
        principals: [new iam.AnyPrincipal()]
      })
    );

    const imageAsset = new ecr_assets.DockerImageAsset(this, 'S2Image', {
      directory: '.',
      platform: ecr_assets.Platform.LINUX_AMD64,
    });
    const jobRole = new iam.Role(this, 'BatchJobRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });
    jobRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        's3:PutObject',
        's3:GetObject',
        's3:ListBucket',
        's3:DeleteObject',
        's3:PutObjectAcl'
      ],
      resources: [
        bucket.bucketArn,
        `${bucket.bucketArn}/*`
      ],
    }));

    jobRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchLogsFullAccess')
    );

    const vpc = ec2.Vpc.fromLookup(this, 'ImportedVPC', {
      vpcId: props.vpcId,
    });

    const subnets = props.subnetIds.map((subnetId, index) =>
      ec2.Subnet.fromSubnetId(this, `Subnet${index}`, subnetId)
    );

    for (const subnetId of props.subnetIds) {
      new cr.AwsCustomResource(this, `EnablePublicIP-${subnetId}`, {
        onCreate: {
          service: 'EC2',
          action: 'modifySubnetAttribute',
          parameters: {
            SubnetId: subnetId,
            MapPublicIpOnLaunch: { Value: true },
          },
          physicalResourceId: cr.PhysicalResourceId.of(`EnablePublicIP-${subnetId}`),
        },
        policy: cr.AwsCustomResourcePolicy.fromSdkCalls({
          resources: cr.AwsCustomResourcePolicy.ANY_RESOURCE,
        }),
      });
    }
    const securityGroup = new ec2.SecurityGroup(this, 'BatchSecurityGroup', {
      vpc,
      description: 'Security group for AWS Batch compute environment',
      allowAllOutbound: true,
    });
    securityGroup.addIngressRule(
      securityGroup,
      ec2.Port.tcp(443),
      'Allow HTTPS from Batch tasks to VPC endpoints'
    );
    new ec2.InterfaceVpcEndpoint(this, 'EcrApiEndpoint', {
      vpc,
      service: ec2.InterfaceVpcEndpointAwsService.ECR,
      subnets: { subnets },
      securityGroups: [securityGroup],
    });

    new ec2.InterfaceVpcEndpoint(this, 'EcrDkrEndpoint', {
      vpc,
      service: ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
      subnets: { subnets },
      securityGroups: [securityGroup],
    });

    new ec2.InterfaceVpcEndpoint(this, 'LogsEndpoint', {
      vpc,
      service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
      subnets: { subnets },
      securityGroups: [securityGroup],
    });
    const computeEnv = new batch.CfnComputeEnvironment(this, 'FargateSpotEnv', {
      type: 'MANAGED',
      state: 'ENABLED',
      computeResources: {
        type: 'FARGATE_SPOT',
        maxvCpus: 256,
        subnets: props.subnetIds,
        securityGroupIds: [securityGroup.securityGroupId],
      },
      serviceRole: new iam.Role(this, 'BatchServiceRole', {
        assumedBy: new iam.ServicePrincipal('batch.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSBatchServiceRole')
        ]
      }).roleArn
    });
    const queue = new batch.CfnJobQueue(this, 'Queue', {
      priority: 1,
      state: 'ENABLED',
      computeEnvironmentOrder: [
        {
          computeEnvironment: computeEnv.attrComputeEnvironmentArn,
          order: 1,
        },
      ],
    });
    const grabDef = new batch.CfnJobDefinition(this, 'GrabJobDef', {
      type: 'container',
      platformCapabilities: ['FARGATE'],
      containerProperties: {
        image: imageAsset.imageUri,
        command: ['python', 'sentinel2_grab.py'],
        fargatePlatformConfiguration: {
          platformVersion: 'LATEST'
        },
        resourceRequirements: [
          { type: 'VCPU', value: '4' },
          { type: 'MEMORY', value: '16384' }
        ],
        executionRoleArn: new iam.Role(this, 'GrabExecutionRole', {
          assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
          managedPolicies: [
            iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy')
          ]
        }).roleArn,
        jobRoleArn: jobRole.roleArn,
        environment: [
          { name: 'OUTPUT_BUCKET', value: bucket.bucketName }
        ],
      },
      retryStrategy: {
        attempts: 2
      },
      timeout: {
        attemptDurationSeconds: Duration.hours(2).toSeconds()
      }
    });
    grabDef.addOverride(
      'Properties.ContainerProperties.NetworkConfiguration',
      { AssignPublicIp: 'ENABLED' },
    );

    const deltaDef = new batch.CfnJobDefinition(this, 'DeltaJobDef', {
      type: 'container',
      platformCapabilities: ['FARGATE'],
      containerProperties: {
        image: imageAsset.imageUri,
        command: ['python', 'sentinel2_delta.py'],
        fargatePlatformConfiguration: {
          platformVersion: 'LATEST'
        },
        resourceRequirements: [
          { type: 'VCPU', value: '4' },
          { type: 'MEMORY', value: '16384' }
        ],
        executionRoleArn: new iam.Role(this, 'DeltaExecutionRole', {
          assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
          managedPolicies: [
            iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy')
          ]
        }).roleArn,
        jobRoleArn: jobRole.roleArn,
        environment: [
          { name: 'OUTPUT_BUCKET', value: bucket.bucketName }
        ],
      },
      retryStrategy: {
        attempts: 2
      },
      timeout: {
        attemptDurationSeconds: Duration.hours(2).toSeconds()
      }
    });
    deltaDef.addOverride(
      'Properties.ContainerProperties.NetworkConfiguration',
      { AssignPublicIp: 'ENABLED' },
    );

const generateDatesFunction = new lambda.Function(this, 'GenerateDatesFunction', {
  runtime: lambda.Runtime.PYTHON_3_9,
  handler: 'index.lambda_handler',
  code: lambda.Code.fromInline(`
import datetime
import json

def lambda_handler(event, context):
    start_date = datetime.datetime.strptime(event['start_date'], '%Y-%m-%d')
    end_date = datetime.datetime.strptime(event['end_date'], '%Y-%m-%d')
    interval_days = event.get('interval_days', 16)
    current_date = start_date
    dates = []
    while current_date <= end_date:
        dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += datetime.timedelta(days=interval_days)
    return {
        'dates': dates,
        'bbox': event['bbox'],
        'layers': event.get('layers', ['ndvi', 'rgb']),
        'location': event['location'],
        'bucket': event.get('bucket', '${bucket.bucketName}')
    }
  `),
  timeout: Duration.minutes(1),
});

const generateDatesTask = new tasks.LambdaInvoke(this, 'GenerateDates', {
  lambdaFunction: generateDatesFunction,
  outputPath: '$.Payload',
});

const processDatesMap = new sfn.Map(this, 'ProcessDates', {
  maxConcurrency: 10,
  itemsPath: '$.dates',
  parameters: {
    'date.$': '$$.Map.Item.Value',
    'bbox.$': '$.bbox',
    'layers.$': '$.layers',
    'location.$': '$.location',
    'bucket.$': '$.bucket'
  }
});

const buildCommandFunction = new lambda.Function(this, 'BuildCommandFunction', {
  runtime: lambda.Runtime.PYTHON_3_9,
  handler: 'index.lambda_handler',
  code: lambda.Code.fromInline(`
import json

def lambda_handler(event, context):
    command = [
        "python", "sentinel2_grab.py",
        "--bbox",
        str(event['bbox'][0]),
        str(event['bbox'][1]),
        str(event['bbox'][2]),
        str(event['bbox'][3]),
        "--date", event['date'],
        "--layers"
    ] + event['layers'] + [
        "--location", event['location'],
        "--bucket", event['bucket']
    ]
    return {
        "command": command,
        "bucket": event['bucket'],
        "location": event['location'],
        "date": event['date']
    }
  `),
  timeout: Duration.seconds(10),
});

const buildCommand = new tasks.LambdaInvoke(this, 'BuildCommand', {
  lambdaFunction: buildCommandFunction,
  outputPath: '$.Payload',
});

const submitBatchJobTask = new sfn.CustomState(this, 'SubmitBatchJob', {
  stateJson: {
    Type: 'Task',
    Resource: 'arn:aws:states:::batch:submitJob.sync',
    Parameters: {
      'JobName.$': "States.Format('grab-{}-{}', $.location, $.date)",
      'JobQueue': queue.ref,
      'JobDefinition': grabDef.ref,
      'ContainerOverrides': {
        'Command.$': '$.command',
        'Environment': [
          {
            Name: 'OUTPUT_BUCKET',
            'Value.$': '$.bucket'
          }
        ]
      }
    },
    ResultPath: '$.batchResult'
  }
});

processDatesMap.iterator(
  buildCommand.next(submitBatchJobTask)
);

const stateMachine = new sfn.StateMachine(this, 'Sentinel2TimeSeries', {
  definition: generateDatesTask.next(processDatesMap),
  timeout: Duration.hours(24),
  role: new iam.Role(this, 'Sentinel2TimeSeriesRole', {
    assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
    inlinePolicies: {
      'BatchJobSubmission': new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            actions: ['batch:SubmitJob', 'batch:DescribeJobs', 'batch:TerminateJob'],
            resources: ['*']
          }),
          new iam.PolicyStatement({
            actions: ['events:PutTargets', 'events:PutRule', 'events:DescribeRule'],
            resources: [`arn:aws:events:${this.region}:${this.account}:rule/StepFunctionsGetEventsForBatchJobsRule`]
          }),
          new iam.PolicyStatement({
            actions: ['lambda:InvokeFunction'],
            resources: [generateDatesFunction.functionArn, buildCommandFunction.functionArn]
          })
        ]
      })
    }
  })
});



    new cdk.CfnOutput(this, 'BucketName', {
      value: bucket.bucketName,
      description: 'S3 bucket for storing satellite imagery',
    });

    new cdk.CfnOutput(this, 'QueueName', {
      value: queue.ref,
    });

    new cdk.CfnOutput(this, 'GrabJobDefArn', {
      value: grabDef.ref,
    });

    new cdk.CfnOutput(this, 'DeltaJobDefArn', {
      value: deltaDef.ref,
    });

    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: stateMachine.stateMachineArn,
      description: 'ARN of the Sentinel-2 time series state machine',
    });
  }
}
