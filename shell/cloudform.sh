
#!/bin/bash
# aws cloudformation create-stack --stack-name SSMParametersStack --template-body ../cfn/cfn-ssm.yaml
aws cloudformation create-stack --stack-name KafkaStreamsStack --template-body ../cfn/cfn-kafka-streams-msk.yaml
aws cloudformation create-stack --stack-name FargateECSStack --template-body ../cfn/cfn-ecs-fargate.yaml
aws cloudformation create-stack --stack-name SSMParamsS3BucketsStack --template-body ../cfn/cfn-s3-ssm.yaml
aws cloudformation create-stack --stack-name StartStepFunctionDailyStack --template-body ../cfn/cfn-eventbridge_sf.yaml

# https://github.com/aws-samples/emr-serverless-samples/blob/main/cfn/emr-serverless-cloudwatch-dashboard/README.md
# replace <Application Id> with id of EMR Serverless application, created in AWS EMR Studio

aws cloudformation create-stack --region <region> \
    --stack-name emr-serverless-dashboard \
    --template-body <file:///path/emr_serverless_cloudwatch_dashboard.yaml> \
    --parameters ParameterKey=ApplicationID,ParameterValue=<Application Id>