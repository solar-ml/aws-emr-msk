# arn:aws:lambda:eu-central-1:123456789012:function:get_predict_fault_status
# This function gets the status of the predict_fault job and returns it

import boto3


def lambda_handler(event, context):
    # Get the job ID from the event
    job_run_id = event["predict_job_id"]

    ssm = boto3.client("ssm")
    # EMR Serverless application is created beforehand and re-used between the steps
    emr = boto3.client("emr-serverless")
    app_id = ssm.get_parameter(Name="emr-app-id")["Parameter"]["Value"]

    response = emr.get_job_run(applicationId=app_id, jobRunId=job_run_id)
    jr_response = response.get("jobRun")
    status = jr_response.get("state")

    # Possible status values 'SUBMITTED'|'PENDING'|'SCHEDULED'|'RUNNING'|'SUCCESS'|'FAILED'|'CANCELLING'|'CANCELLED',
    return status
