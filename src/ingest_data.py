# Purpose: First script of the pipeline.
# Reads PV array sensors data in batches from Kafka topic 
# and applies CWT transformation on per-device basis to 4 series of sensor readings 
# Author:  VK.
# Date: 2023-05-05

import datetime
import os
from collections import namedtuple

import boto3
import numpy as np
import pywt
from ec2_metadata import ec2_metadata
from pyspark.ml.feature import MinMaxScaler
from pyspark.ml.linalg import Vectors, VectorUDT
from pyspark.sql import SparkSession
from pyspark.sql.functions import collect_list, from_json, row_number, udf
from pyspark.sql.types import (ArrayType, FloatType, StringType, StructField,
                               StructType, TimestampType)
from pyspark.sql.window import Window

topic_input = "solar.data.segment.01"
os.environ['AWS_DEFAULT_REGION'] = ec2_metadata.region
ssm_client = boto3.client("ssm")


def main():
    # Retrieve params from AWS System Manager Parameter Store
    params = get_parameters()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("SolarPVDataIngestion") \
        .getOrCreate()
    
    # timestamps.start -> 0:00 of day-1
    # timestamps.end -> 23:59:59:(9) of day-1
    timestamps = get_previous_day_timestamps()
    
    solar_pv_data = read_from_kafka(spark, params, timestamps.start, timestamps.end)
    
    # Define the schema for the incoming data
    schema = StructType([
        StructField("deviceID", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("voltage", FloatType(), True),
        StructField("current", FloatType(), True),
        StructField("temperature", FloatType(), True),
        StructField("irradiance", FloatType(), True)
    ])
    
    # Deserialize the Kafka value (message) from binary to string
    solar_pv_data = solar_pv_data.selectExpr("CAST(key AS STRING) AS deviceID", "CAST(value AS STRING) AS value")

    # Convert the value (message) to JSON and parse it into columns using the defined schema
    df_24h = solar_pv_data.select("deviceID", from_json("value", schema).alias("data")).select("deviceID", "data.*")
   
    # format can also be AVRO, for that we need to define required schema 
    # file continues below... 
    
    # apply CWT transform
    df_24h = process_data_cwt(df_24h)
    
    # outpit processed file to S3 silver (staging bucket)
    write_data(df_24h, params["silver_bucket"])
    

def process_data_cwt(df_24h):
    """
    Applies CWT tranformation to 4 sensor readings within window of deviceID
    """
    sensor_list = ["voltage", "current", "temperature", "irradiance"]

    # Since CWT cannot be applied uniformly, but rather on a per-device, per-feature basis
    # Create a window partitioned by deviceID and ordered by timestamp
    window_spec = Window.partitionBy("deviceID").orderBy("timestamp")

    # Define the function to apply the CWT
    def apply_cwt(data, scales, wavelet):
        coefficients, _ = pywt.cwt(data, scales, wavelet)
        return coefficients

    # Create a UDF to apply the CWT for each sensor within a window
    apply_cwt_window_udf = udf(
        lambda data: [apply_cwt(np.array(window_data), np.arange(1, 65), "morl").tolist() for window_data in data],
        ArrayType(ArrayType(ArrayType(FloatType()))),
    )

    # Apply CWT to each sensor data and normalize the scalograms
    # to_vector_udf() is a UDF that takes a 2D array as input and returns a dense vector. 
    # It is used to convert the 2D CWT coefficients into vectors so that they can be normalized using MinMaxScaler
    to_vector_udf = udf(lambda x: Vectors.dense(x.flatten()), VectorUDT())

    for sensor in sensor_list:
        # Collect sensor data within the window
        df_24h = df_24h.withColumn(f"{sensor}_window_data", collect_list(sensor).over(window_spec))

        # Apply CWT within the window
        df_24h = df_24h.withColumn(f"{sensor}_cwt", apply_cwt_window_udf(f"{sensor}_window_data"))

        # Convert the 2D CWT coefficients into vectors
        df_24h = df_24h.withColumn(f"{sensor}_cwt_vector", to_vector_udf(f"{sensor}_cwt"))

        # Create a MinMaxScaler instance for each sensor
        scaler = MinMaxScaler(inputCol=f"{sensor}_cwt_vector", outputCol=f"normalized_{sensor}_cwt_vector")

        # Normalize the scalograms (vectors) for each sensor
        scaler_model = scaler.fit(df_24h)
        df_24h = scaler_model.transform(df_24h)

    # Drop unnecessary columns
    for sensor in sensor_list:
        df_24h = df_24h.drop(f"{sensor}_cwt", f"{sensor}_cwt_vector", f"{sensor}_window_data")
    
    return df_24h
       

def read_from_kafka(spark, params, start, end):
    options_read = {
        "kafka.bootstrap.servers": params["kafka_servers"],
        "subscribe": topic_input,
        "startingOffsetsByTimestamp": f"{{{topic_input} : {start}}}",
        "endingOffsetsByTimestamp": f"{{{topic_input} : {end}}}",
        "kafka.ssl.truststore.location": "/tmp/kafka.client.truststore.jks",
        "kafka.security.protocol": "SASL_SSL",
        "kafka.sasl.mechanism": "AWS_MSK_IAM",
        "kafka.sasl.jaas.config":
            "software.amazon.msk.auth.iam.IAMLoginModule required;",
        "kafka.sasl.client.callback.handler.class":
            "software.amazon.msk.auth.iam.IAMClientCallbackHandler"
    }
    
    # Load data from previous day from Kafka using batch mode
    df_data = spark.read \
        .format("kafka") \
        .options(**options_read) \
        .load()
    
    return df_data


def get_previous_day_timestamps():
    """Returns start and end of the previous day in the timestamp format packed into NamedTuple"""
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


def write_data(df_24h, silver_bucket):
    """Write processed data in Parquet format to S3 silver (staging) bucket"""
    timestamps = get_previous_day_timestamps()
    start_timestamp = timestamps.start.strftime("%Y-%m-%dT%H-%M-%S")
    end_timestamp = timestamps.end.strftime("%Y-%m-%dT%H-%M-%S")
    
    # Define the path for the output Parquet file
    file_name = f"{topic_input}_{start_timestamp}_to_{end_timestamp}.parquet"
    output_path = f"s3a://{silver_bucket}/{file_name}"

    # Save the DataFrame as a Parquet file on the specified S3 bucket
    df_24h.write.parquet(output_path, mode="overwrite")


def get_parameters():
    """Load parameter values from AWS Systems Manager (SSM) Parameter Store"""

    params = {
        "kafka_servers": ssm_client.get_parameter(
            Name="/kafka_spark_demo/kafka_servers")["Parameter"]["Value"],
        "silver_bucket": ssm_client.get_parameter(
            Name="/kafka_spark_demo/silver_bucket")["Parameter"]["Value"],
    }

    return params


if __name__ == "__main__":
    main()