# arn:aws:lambda:us-east-1:123456789012:function:query_results
# This function queries parquet based on deviceID and return JSON result

import json
import boto3
import pyarrow.parquet as pq

s3 = boto3.resource('s3')
bucket = s3.Bucket('gold-bucket')
parquet_file = 'some_file.parquet'

def lambda_handler(event, context):
    # Get the deviceID from the query string
    deviceID = event['queryStringParameters']['deviceID']
    
    # Read the parquet file from S3
    obj = bucket.Object(parquet_file)
    data = obj.get()['Body'].read()
    table = pq.read_table(data)
    
    # Filter the table by deviceID
    filtered_table = table.filter(table['deviceID'] == deviceID)
    
    # Convert the filtered table to JSON
    json_data = filtered_table.to_pydict()
    
    # Return the JSON response
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps(json_data)
    }