# arn:aws:lambda:us-east-1:123456789012:function:ingest_data
# This function runs the ingest_data.py script on EMR Serverless and returns the job ID

import boto3


def lambda_handler(event, context):
    def get_job_run(client, app_id: str, job_run_id: str) -> dict:
        response = client.get_job_run(applicationId=app_id, jobRunId=job_run_id)
        return response.get("jobRun")

    ssm = boto3.client("ssm")
    kafka_uris = ssm.get_parameter(Name="kafka-servers")["Parameter"]["Value"]
    kafka_topics = ssm.get_parameter(Name="kafka-topics")["Parameter"]["Value"]
    
    # EMR Serverless application is created beforehand and re-used between the steps
    emr = boto3.client("emr-serverless")
    application_id = ssm.get_parameter(Name="emr-app-id")["Parameter"]["Value"]
    
    # S3 bucket for EMR logs
    log_bucket = ssm.get_parameter(Name="log-bucket")["Parameter"]["Value"]

    response = emr.start_job_run(
        applicationId=application_id,
        executionRoleArn="arn:aws:iam::123456789012:role/EMRServerlessExecutionRole",
        jobDriver={
            "sparkSubmit": {
                "entryPoint": "s3://bootstrap/spark/ingest_data.py",
                # for now kafka-topic is hard coded in `ingest_data.py`
                # and kafka_uris is obtained from SSM
                "entryPointArguments": [kafka_uris, kafka_topics],
                "sparkSubmitParameters": "--conf spark.executor.cores=1 --conf spark.executor.memory=4g --conf spark.driver.cores=1 --conf spark.driver.memory=4g --conf spark.executor.instances=1",
            }
        },
        configurationOverrides={
            "monitoringConfiguration": {"s3MonitoringConfiguration": {"logUri": f"s3://{log_bucket}/emr"}}
        },
    )

    job_run_id = response.get("jobRunId")

    # we replace these frequent checks in favor or polling
    # wait = True
    # job_done = False
    # while wait and not job_done:
    #     jr_response = get_job_run(client, application_id, job_run_id)
    #     # 'state': 'SUBMITTED'|'PENDING'|'SCHEDULED'|'RUNNING'|'SUCCESS'|'FAILED'|'CANCELLING'|'CANCELLED',
    #     job_done = jr_response.get("state") in [
    #         "SUCCESS",
    #         "FAILED",
    #         "CANCELLING",
    #         "CANCELLED",
    #     ]

    return job_run_id
