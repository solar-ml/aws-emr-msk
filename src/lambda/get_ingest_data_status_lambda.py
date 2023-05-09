# arn:aws:lambda:us-east-1:123456789012:function:get_ingest_data_status
# This function gets the status of the ingest_data job and returns it

import boto3

def lambda_handler(event, context):
  # Get the job ID from the event
  job_id = event['job_id']

  # Get the EMR job status
  emr = boto3.client('emr-containers')
  response = emr.describe_job_run(virtualClusterId='vc-123456789012', id=job_id)
  status = response['jobRun']['state']

  # Return the status
  return status