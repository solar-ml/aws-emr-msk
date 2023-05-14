# arn:aws:lambda:eu-central-1:123456789012:function:notify_success
# This function sends a notification to an SNS topic when the pipeline succeeds

import boto3

def lambda_handler(event, context):
    # Get the SNS topic ARN from the Parameter Store
    ssm = boto3.client('ssm')
    sns_topic = ssm.get_parameter(Name='sns-topic')['Parameter']['Value']

    # Create a message with the pipeline details
    message = f"The data pipeline has completed successfully.\n"
    message += f"Ingest data job ID: {event['ingest_job_id']}\n"
    message += f"Predict fault job ID: {event['predict_job_id']}\n"

    # Publish the message to the SNS topic
    sns = boto3.client('sns')
    response = sns.publish(TopicArn=sns_topic, Message=message)

    # Return the response
    return response