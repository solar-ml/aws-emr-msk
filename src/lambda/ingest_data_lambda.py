# arn:aws:lambda:us-east-1:123456789012:function:ingest_data
# This function runs the ingest_data.py script on EMR Serverless and returns the job ID

import boto3

def lambda_handler(event, context):
    # Get the Kafka cluster URIs and topic names from the Parameter Store
    ssm = boto3.client('ssm')
    kafka_uris = ssm.get_parameter(Name='kafka_uris')['Parameter']['Value']
    kafka_topics = ssm.get_parameter(Name='kafka_topics')['Parameter']['Value']

    # Create an EMR job request with the ingest_data.py script and the Kafka parameters
    emr = boto3.client('emr-containers')
    job_request = {
        "name": "IngestData",
        "virtualClusterId": "vc-123456789012",
        "executionRoleArn": "arn:aws:iam::123456789012:role/EMRContainersExecutionRole",
        "releaseLabel": "emr-6.3.0-latest",
        "jobDriver": {
        "sparkSubmitJobDriver": {
            "entryPoint": "s3://bootstrap/ingest_data.py",
            "entryPointArguments": [kafka_uris, kafka_topics],
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
