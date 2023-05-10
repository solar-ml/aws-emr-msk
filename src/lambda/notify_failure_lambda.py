# arn:aws:lambda:us-east-1:123456789012:function:notify_failure
# This function sends a notification to an SNS topic when the pipeline fails

import boto3

def lambda_handler(event, context):
    # Get the SNS topic ARN from the Parameter Store
    ssm = boto3.client('ssm')
    sns_topic = ssm.get_parameter(Name='sns-topic')['Parameter']['Value']

    # Create a message with the pipeline details and the error
    message = f"The data pipeline has failed.\n"
    message += f"Error: {event['Error']}\n"
    message += f"Cause: {event['Cause']}\n"

    # Publish the message to the SNS topic
    sns = boto3.client('sns')
    response = sns.publish(TopicArn=sns_topic, Message=message)

    # Return the response
    return response