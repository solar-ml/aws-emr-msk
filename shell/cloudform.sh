
#!/bin/bash
aws cloudformation create-stack --stack-name SSMParametersStack --template-body ../cloudformation/ssm.yaml
aws cloudformation create-stack --stack-name S3BucketsStack --template-body ../cloudformation/s3.yaml
aws cloudformation create-stack --stack-name StartStepFunctionDailyStack --template-body ../cloudformation/eventbridge_sf.yaml

# https://github.com/aws-samples/emr-serverless-samples/blob/main/cloudformation/emr-serverless-cloudwatch-dashboard/README.md
aws cloudformation create-stack --region <region> \
    --stack-name emr-serverless-dashboard \
    --template-body <file:///path/emr_serverless_cloudwatch_dashboard.yaml> \
    --parameters ParameterKey=ApplicationID,ParameterValue=<Application Id>