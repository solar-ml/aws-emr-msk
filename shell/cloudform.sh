
#!/bin/bash
aws cloudformation create-stack --stack-name SSMParametersStack --template-body ../cloudformation/ssm.yml
aws cloudformation create-stack --stack-name S3BucketsStack --template-body ../cloudformation/s3.yml
aws cloudformation create-stack --stack-name StartStepFunctionDailyStack --template-body ../cloudformation/eventbridge_sf.yml

