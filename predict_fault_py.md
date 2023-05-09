## Python code: predict_fault.py
#solar_pipeline

Second script in pipeline `predict_fault.py` loads parquet file, feeds into pre-trained LeNet, gets its prediction classes, appends classes as extra column and stores result in gold S3 bucket. The names of the silver and gold S3 buckets are also obtained from the AWS System Manager Parameter Store. 

```python
# Purpose: Second script of the pipeline loads Parquet file, feeds into pre-trained
# LeNet, gets its prediction classes, appends classes as extra column and
# saves result into gold S3 bucket. 
# Author:  VK.
# Date: 2023-05-05

import datetime
import os
from collections import namedtuple

import boto3
import numpy as np
import pandas as pd
import tensorflow as tf
from botocore.exceptions import ClientError
from ec2_metadata import ec2_metadata
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

topic_input = "solar.data.segment.01"
os.environ['AWS_DEFAULT_REGION'] = ec2_metadata.region
ssm_client = boto3.client("ssm")

def get_previous_day_timestamps():
    # Define the named tuple
    Timestamps = namedtuple("Timestamps", ["start", "end"])

    # Get the current date and time
    now = datetime.datetime.now()

    # Calculate starting and ending timestamps for the previous day
    starting_timestamp = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(days=1)
    ending_timestamp = starting_timestamp + datetime.timedelta(days=1, milliseconds=-1)

    # Convert to milliseconds - by multiplying by 1000, 
    # we ensure that the timestamps are compatible with the Kafka offsets 
    starting_timestamp = starting_timestamp.timestamp() * 1000
    ending_timestamp = ending_timestamp.timestamp() * 1000

    # Return the named tuple
    return Timestamps(start=starting_timestamp, end=ending_timestamp)


def check_parquet_exists(s3, bucket, file_name):
    try:
        s3.head_object(Bucket=bucket, Key=file_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            raise


def load_cnn_model(model_path):
    model = tf.keras.models.load_model(model_path)
    return model


def predict_fault_class(model, scalograms):
    predictions = model.predict(scalograms)
    fault_classes = predictions.argmax(axis=1)
    return fault_classes


def main():    
    # Retrieve params from AWS System Manager Parameter Store
    params = get_parameters()
    
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CNNFaultPrediction") \
        .getOrCreate()

    silver_bucket = params["silver_bucket"]
    gold_bucket = params["gold_bucket"]
    
    s3 = boto3.client('s3')

    # Check if the parquet file exists
    timestamps = get_previous_day_timestamps()
    start_timestamp = timestamps.start.strftime("%Y-%m-%dT%H-%M-%S")
    end_timestamp = timestamps.end.strftime("%Y-%m-%dT%H-%M-%S")
    file_name = f"{topic_input}_{start_timestamp}_to_{end_timestamp}.parquet"

    if check_parquet_exists(s3, silver_bucket, file_name):
        # Load the parquet file into a Spark DataFrame
        input_path = f"s3://{silver_bucket}/{file_name}"
        df = spark.read.parquet(input_path)

        # Load the pre-trained LeNet CNN model
        model_path = "le_net_2023_6_class.h5"
        cnn_model = load_cnn_model(model_path)

        # Collect the DataFrame into a Pandas DataFrame for further processing
        df_pd = df.toPandas()
        
        sensor_list = ["voltage", "current", "temperature", "irradiance"]

        # Prepare data for prediction
        X = np.stack([df_pd[f"normalized_{sensor}_cwt_vector"] for sensor in sensor_list], axis=-1)

        # Predict fault classes using the loaded model
        fault_classes = predict_fault_class(cnn_model, X)

        # Add the predicted fault class as a new column
        df_pd['fault_class'] = fault_classes

        # Convert the Pandas DataFrame back to a PySpark DataFrame
        df_with_fault_class = spark.createDataFrame(df_pd)

        # Save the DataFrame with fault class to the processed S3 bucket
        output_path = f"s3://{gold_bucket}/{file_name}"
        df_with_fault_class.write.parquet(output_path)
        
        print(f"Predictions saved to {output_path}")
    else:
        print(f"Parquet file for topic {topic_input} does not exist in the {silver_bucket} bucket")


def get_parameters():
    """Load parameter values from AWS Systems Manager (SSM) Parameter Store"""

    params = {       
        "silver_bucket": ssm_client.get_parameter(
            Name="silver-bucket")["Parameter"]["Value"],
        "gold_bucket": ssm_client.get_parameter(
            Name="gold-bucket")["Parameter"]["Value"],
    }

    return params


if __name__ == "__main__":
    main()

```