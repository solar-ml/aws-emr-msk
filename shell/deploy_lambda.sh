#!/bin/bash
# Package and deployment of Lambdas to AWS
# Make sure to set AWS profile, region, and S3 bucket for deployment
AWS_PROFILE="your_aws_profile"
AWS_REGION="your_aws_region"
S3_BUCKET="your_s3_bucket"

# Package and deploy Lambda functions with just boto3 as a dependency
lambdas_boto3="get_ingest_data_status_lambda \
               notify_failure_lambda \
               get_predict_fault_status_lambda \
               notify_success_lambda \
               ingest_data_lambda \
               predict_fault_lambda"

# Package and deploy Lambda functions with boto3 and pyarrow as dependencies
lambdas_boto3_pyarrow="query_results_lambda"

# Function to package and deploy a Lambda function
package_and_deploy_lambda() {
  lambda_function=$1
  requirements_file=$2

  echo "Packaging and deploying $lambda_function..."

  # Create a virtual environment and install dependencies
  python -m venv $lambda_function/venv
  source $lambda_function/venv/bin/activate
  pip install -r $requirements_file

  # Package the Lambda function along with its dependencies
  mkdir -p $lambda_function/package
  cd $lambda_function/venv/lib/python*/site-packages
  cp -r ./* ../../../package
  cp -r ../../../$lambda_function.py ../../../package
  cd ../../../package
  zip -r ../$lambda_function.zip .

  # Upload the packaged Lambda function to AWS Lambda
  aws s3 cp ../$lambda_function.zip s3://$S3_BUCKET/ --profile $AWS_PROFILE
  aws lambda update-function-code \
    --function-name $lambda_function \
    --s3-bucket $S3_BUCKET \
    --s3-key $lambda_function.zip \
    --region $AWS_REGION \
    --profile $AWS_PROFILE

  # Clean up
  deactivate
  cd ..
  rm -rf venv package $lambda_function.zip

  echo "Completed deploying $lambda_function"
  echo
}

# Package and deploy Lambda functions
for lambda_function in $lambdas_boto3
do
  package_and_deploy_lambda $lambda_function "requirements_boto3.txt"
done

for lambda_function in $lambdas_boto3_pyarrow
do
  package_and_deploy_lambda $lambda_function "requirements_boto3_pyarrow.txt"
done

echo "All Lambda functions have been deployed."
