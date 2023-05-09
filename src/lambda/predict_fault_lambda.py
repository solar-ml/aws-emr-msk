# arn:aws:lambda:us-east-1:123456789012:function:predict_fault
# This function runs the predict_fault.py script on EMR Serverless and returns the job ID

import boto3

def lambda_handler(event, context):
    # Get the names of the silver and gold S3 buckets from the Parameter Store
    ssm = boto3.client('ssm')
    silver_bucket = ssm.get_parameter(Name='silver_bucket')['Parameter']['Value']
    gold_bucket = ssm.get_parameter(Name='gold_bucket')['Parameter']['Value']

    # Create an EMR job request with the predict_fault.py script and the S3 buckets
    emr = boto3.client('emr-containers')
    job_request = {
        "name": "PredictFault",
        "virtualClusterId": "vc-123456789012",
        "executionRoleArn": "arn:aws:iam::123456789012:role/EMRContainersExecutionRole",
        "releaseLabel": "emr-6.3.0-latest",
        "jobDriver": {
        "sparkSubmitJobDriver": {
            "entryPoint": "s3://bootstrap/predict_fault.py",
            "entryPointArguments": [silver_bucket, gold_bucket],
            "sparkSubmitParameters": "--conf spark.executor.instances=2 --conf spark.executor.memory=4G --conf spark.driver.cores=1"
        }
        },
        "configurationOverrides": {
        "applicationConfiguration": [
            {
            "classification": "spark-defaults",
            "properties": {
                "spark.dynamicAllocation.enabled": "false"
            }
            }
        ]
        }
    }

    # Submit the EMR job and get the job ID
    response = emr.start_job_run(jobRunRequest=job_request)
    job_id = response['id']

    # Return the job ID
    return job_id