## Problem description

Electrical faults in photovoltaic (PV) systems may evolve due to several abnormalities in internal configuration. We are presented with the task of **building an early detection and fault classification algorithm that uses the available electrical and environmental measurements from the sensors** deployed by most manufacturers of PV equipment.

Figure 1 shows a typical PV system configuration consisting of a 5 × 3 PV panel and a boost converter programmed with the MPPT algorithm to operate the PV module at the maximum power point (MPP). The locations of typical photovoltaic panel problems are shown symbolically.
![](i/panel_schema.jpg)

Normally each panel of the PV system is equipped with four sensors, namely: `voltage`, `current`, `temperature` and `irradiance` in addition to disconnection circuit and a servo motor. All of these components are connected to the microcontroller unit which periodically (every 20 seconds) send readings to the remote terminal unit followed by the SCADA (Supervisory control and data acquisition) system.

### Incoming data 

The data represents the electrical and environmental readings of the 10k PV arrays installed in the solar plant system. The readings are logged into a SCADA system, which uses a `kafka-producer` application to stream into Apache Kafka, deployed either on-premises or in the cloud. In our case - into Amazon Managed Streaming for Apache Kafka (Amazon MSK) into a topic named `solar.data.segment.01`.

The incoming data contains the readings taken by the four sensors, together with the `deviceID` and `timestamp`. Schema presented below:

```python
schema = StructType([
        StructField("deviceID", StringType(), True), # 10 alphanum chars UTF-8, 10 bytes
        StructField("timestamp", TimestampType(), True), # TimestampType in PySpark, 8 bytes
        StructField("voltage", FloatType(), True), # 4 bytes
        StructField("current", FloatType(), True), # 4 bytes
        StructField("temperature", FloatType(), True), # 4 bytes
        StructField("irradiance", FloatType(), True) # bytes
    ])
```
Each data point in binary format takes 10 + 8 + 16 = 34 bytes. To estimate the size of the incoming data stream, we consider the size of each data point and the rate at which they are generated. Supposedly, readings from 4 sensors installed on 10,000 solar panels are collected in the SCADA system every 20 seconds and consumed once every 24 hours.

Number of data points per device in 24 hours = (24 hours * 60 minutes/hour * 60 seconds/minute) / 20 seconds = 4,320. Total number of data points from all devices in 24 hours = 10,000 devices * 4,320 data points/device = 43,200,000 data points. Total daily batch size = 43,200,000 data points * 34 bytes/data point = 1,468,800,000 bytes = **1.47GB** or **1.37GiB** per day. As per requirements, the data is collected once a day according to a schedule.

### Architectural choices for data processing

From a high-level overview, the data pipeline consists of two major steps: 

1. The first involves consuming the batch data from the Kafka topic with PySpark, applying wavelet signal processing to each of the 4 time series on a per-device basis, and saving the processed data to a parquet file in the `silver` staging bucket.

2. Second step involves reading data from `silver` bucket, transforming it into the shape required by neural network and using pre-trained TensorFlow model to classify state of each device into one of six conditions. The data is then stored in the `gold` bucket along with the predictions.

3. From there, data is accessible via API Gateway, which gives access to lambda function that queries parquet based on deviceID and returns JSON result.

Thus, the software requirements of the case prescribe the use of PySpark, TensorFlow and PyWavelets to achieve the intended result.

There are two main components of the solution: data processing and workflow orchestration. AWS offers many services that are well suited for ETL tasks. Each service has its own unique features, strengths and limitations, as well as overlapping functionality. Nevertheless, we will give a brief overview and choose those that fit best in our particular case.  

, and overlap with respect to their capabilities. Each service has its own unique features, strengths, and limitations, so you should choose the one that best meets your specific requirements and preferences.


We will consider between:
- **AWS Glue**, 
- **AWS Data Pipeline**, 
- **Amazon EMR on EC2/EKS** or **Amazon EMR Serverless** with **StepFunctions**,
- **Apache Airflow**. 


That's a good question. AWS provides several tools for big data extract, transform, and load (ETL) processes and analytics, but they have different features and use cases. Here is a brief comparison of AWS Glue vs EMR Serveless vs EMR on EC2/EKS vs AWS Data Pipeline based on the search results¹²³:

| Service | Description | Pros | Cons |
| --- | --- | --- | --- |
| AWS Glue | A serverless data integration service that automates ETL tasks and provides a data catalog. | - Easy to set up and use. - Automatically generates code and metadata. - Supports PySpark and TensorFlow. - Integrates with other AWS services. | - More expensive than EMR. - Limited worker types and memory. - Less flexible and customizable than EMR. |
| EMR Serverless | A serverless runtime environment that simplifies running open-source frameworks like Apache Spark, Hive, and Presto at petabyte scale. | - No need to configure, manage, or scale clusters. - Optimized runtimes for Spark and Hive. - Flexible job execution options. - Supports PySpark and TensorFlow. | - Still in preview mode. - May not support all features of EMR on EC2/EKS/Outpost. - Less control over cluster configuration and management than EMR on EC2/EKS/Outpost. |
| EMR on EC2/EKS/Outpost | A big data platform that allows you to configure your own cluster of EC2 instances or Kubernetes pods to run various Hadoop ecosystem components. | - Complete control over cluster configuration and management. - Supports a wide range of use cases and tools, including machine learning, streaming, SQL queries, etc. - Many supported instance types to choose from. | - Requires more planning, configuration, and scaling of clusters. - More complex and error-prone than serverless options. - May incur higher costs if clusters are not optimized or terminated properly. |
| AWS Data Pipeline | A web service that helps you reliably process and move data between different AWS compute and storage services, as well as on-premises data sources. | - Easy to create data pipelines using a drag-and-drop console or templates. - Supports scheduling, dependency tracking, error handling, and retry logic for data pipelines. - Low cost and pay per use model. | - Does not support PySpark or TensorFlow natively. - Less powerful and scalable than EMR or Glue for ETL tasks. - Limited integration with other AWS services compared to EMR or Glue. |

Depending on your data transformation task requirements, you may choose one or more of these services to suit your needs.

Source: Conversation with Bing, 5/9/2023
(1) Amazon EMR Serverless vs. AWS Glue - missioncloud.com. https://www.missioncloud.com/blog/amazon-emr-serverless-vs-aws-glue.
(2) AWS Glue vs EMR - Medium. https://medium.com/swlh/aws-glue-vs-emr-433b53872b30.
(3) amazon web services - AWS Glue vs EMR Serverless - Stack Overflow. https://stackoverflow.com/questions/70321935/aws-glue-vs-emr-serverless.


### AWS Glue

AWS Glue is a serverless ETL service that automatically discovers, categorizes data, and stores metadata in a data catalog, generating ETL code in Python or Scala. It supports scheduling, dependency tracking, integrates with AWS services like S3, RDS, and Redshift, runs Apache Spark jobs, and offers pay-as-you-go pricing based on data processing units (DPUs) and data catalog usage.

AWS Glue has a graphical interface to create and run ETL jobs using AWS Glue Studio. However, AWS Glue Studio is not a workflow service. It does not allow you to design and monitor complex workflows that involve branching, parallelism, or other logic. It also does not support other types of tasks or integrations besides ETL jobs.

Although Glue supports third-party Python libraries, which you can install using the `--additional-python-modules` parameter, the maximum size of a single dependency file is 50MB, and the total size of all dependencies combined is 250MB. But, the TensorFlow pip package for Linux systems is about 500MB+ (TensorFlow Docker image is about 2 GB).

### AWS Data Pipeline

AWS Data Pipeline is a service designed for data-driven workflows, supporting data movement and transformation, integrating with AWS services like S3, RDS, and EMR, offering scheduling capabilities and dependency tracking, but requiring manual error handling and retries. If the data source you need is not supported, or if you want to perform an activity that is not integrated, you will have to hack your way around with shell scripts.

### Amazon EMR on EC2/EKS or EMR Serverless
![](i/Arch_Amazon-EMR_64.png)

| AWS Glue | EMR Serverless |
| --- | --- |
| Designed for ETL processes and data integration | Designed for data processing and analytics |

EMR services are more appropriate for analytics applications that require high performance processing using open source tools. Since our task is a fairly short-term conversion, continuous operation of the EMR cluster is not financially viable.

Running EMR Serverless can be less expensive and faster than creating and terminating EMR clusters programmatically with AWS CLI or StepFunctions, especially for short-lived and sporadic computing tasks. This is due to the following reasons:

1. Pay-per-use pricing: With EMR Serverless, you only pay for the resources used during job execution, making it cost-efficient for infrequent or unpredictable workloads. You are not billed for idle time between jobs.

2. Resource allocation and scaling: EMR Serverless automatically scales resources based on workload, ensuring you only pay for what you need. In contrast, with EMR on EC2, you may need to over-provision resources to handle peak workloads or under-provision resources during off-peak periods.

Currently EMR Serverless only includes Spark and Hive as pre-installed applications, unlike EMR EC2/EKS where there is a massive selection of libraries. However, this issue is addressed by creating a custom docker image based on the existing `emr-serverless/spark/emr-6.9.0` and adding TensorFlow, NumPy, Pandas and PyWavelets to it.

1. Create a Dockerfile with the following contents:
```
FROM public.ecr.aws/emr-serverless/spark/emr-6.9.0:latest

USER root

# python packages
RUN pip3 install boto3 ec2_metadata
RUN pip3 install numpy pandas pywt tensorflow

# EMR Serverless will run the image as hadoop
USER hadoop:hadoop    
```

2. Build the Docker image 
```shell
docker build -t my-emr-serverless-spark:latest .
```

3. Push image to Amazon Elastic Container Registry (ECR) 
```shell
aws ecr create-repository --repository-name my-emr-serverless-spark
docker tag my-emr-serverless-spark:latest <account_id>.dkr.ecr.<region>.amazonaws.com/my-emr-serverless-spark:latest
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account_id>.dkr.ecr.<region>.amazonaws.com
docker push <account_id>.dkr.ecr.<region>.amazonaws.com/my-emr-serverless-spark:latest
```

4. Reference the custom Docker image in your EMR Serverless job configuration.

```json
{
  "containerInfo": {
    "eciConfig": {
      "repositoryUri": "<account_id>.dkr.ecr.<region>.amazonaws.com/my-emr-serverless-spark:latest"
    }
  }
}
```


### Orchestration approach consideration


The solution uses four S3 buckets:
- Bootstrap bucket – Stores the ingested application logs in Parquet file format.
- Loggregator source bucket – Stores the Scala code and JAR for running the EMR job.
- Loggregator output bucket – Stores the EMR processed output.
- EMR Serverless logs bucket – Stores the EMR process application logs.

SSM PARAMS

kafka-servers
kafka-topics
sns-topic
log-bucket
silver-bucket
gold-bucket
emr-app-id



#### The central piece of the workflow is the **AWS StepFunctions** state machine. It orchestrates two Spark jobs and handle failures and retries. Its execution is triggered by the event scheduled in the **EventBridge**.


### AWS Data Pipeline with EMR Serverless
![](aws_data_pipeline.svg)


### The state machine shown below consists of 10 states, each performing a specific task or decision.

![](i/stepfunctions_graph.svg)

- `IngestData` **task** state triggers a Lambda function [`ingest_data`](<src/lambda/ingest_data_lambda.py>) which is responsible for running the `ingest_data.py` script from S3 `bootstrap` bucket on an EMR Serverless cluster to obtain data from a Kafka cluster. The function takes care of submitting the EMR job and returns the `job_id` for use downstream. If the function encounters an error, it will retry up to 6 times with an exponential backoff strategy. If all retries fail, it moves to the `NotifyFailure` state.

- `WaitForIngestData` **wait** state pauses the state machine for the specified number of seconds in `$.wait_time` before moving to the next state. `$.wait_time` is passed as input parameter to the StepFunction by EventBridge script. This wait time is used to avoid polling the EMR job status too frequently. 

- `GetIngestDataStatus` **task** state triggers a Lambda function `get_ingest_data_status` to retrieve the status of an EMR job by calling `describe_job_run` method on the EMR client and passing the virtual cluster ID and the job ID. If the function encounters an error, it will retry up to 6 times with an exponential backoff strategy. If all retries fail, it moves to the NotifyFailure state.

- `CheckIngestDataStatus` **choice** state evaluates the status of data ingestion. If it has succeeded, it moves to the `PredictFault` state. If it has failed, it moves to the `NotifyFailure` state. If the status is unknown, it moves back to the `WaitForIngestData` state.

- `PredictFault`, `WaitForPredictFault`, `GetPredictFaultStatus`, `CheckPredictFaultStatus` states repeat the same pattern as the 4 steps above, including submitting the second EMR job to EMR Serverless via lambda function call and monitoring its execution state.

- `NotifySuccess` **task** state triggers a Lambda function `notify_success` to send a notification about the successful completion of the Spark jobs. 

- `NotifyFailure` **task** state triggers a Lambda function `notify_failure` to send a notification about the **failure of any of the previous steps**. 

#### Advantages of using the StepFunctions approach:

- **Error handling**: Errors are managed at each Task state, providing a robust way to handle failures.
- **Retries**: Failed Lambda functions are retried with an exponential backoff strategy, reducing the impact of transient errors.
- **Status monitoring**: Continuous checks of Spark job statuses are performed, with appropriate actions taken based on each job's status.
- **Orchestration**: Step Functions simplify complex workflow management by breaking them into smaller, more manageable states.
- **Modularity**: With each state in the workflow having a specific purpose, the overall process becomes easier to understand.

The advantages of this approach are:

It simplifies and automates the orchestration of complex and distributed applications using AWS services.
It provides built-in error handling and retry mechanisms for handling failures and transient errors.
It allows you to monitor and visualize your workflow execution using Step Functions’ graphical console.
It scales automatically with your workload and charges you only for what you use.

Combining the information provided, the advantages of using the StepFunctions approach are:

Simplification and automation: The orchestration of complex and distributed applications using AWS services is streamlined.
Error handling and retries: Built-in mechanisms handle failures and transient errors, while failed Lambda functions are retried with an exponential backoff strategy.
Status monitoring: Spark job statuses are continuously checked, and Step Functions' graphical console allows for easy monitoring and visualization of workflow execution.
Orchestration and modularity: Complex workflows are managed more effectively by breaking them into smaller, more manageable states, each having a specific purpose.
Scalability and cost-effectiveness: The service scales automatically with your workload, charging only for what you use, making it a cost-effective choice for managing workflows




### Further conversion to streaming application

From Amazon MSK the data is ingested into Amazon EMR (Amazon Elastic MapReduce), a Spark/Hadoop/Hive cluster deployed on AWS. For this particular task, we chose a 24-hour batch window. So data is consumed from 0:00 to 23:59:59 the day before the current day. This window can be adjusted and predictive model can be applied more frequently to narrower ranges of data. However, this will incur additional charges from EMR.

Moreover, while we handle batch processing with EMR Serverless within this pipeline it can also be converted into a near real-time streaming application. To achieve this, we can use Spark Structured Streaming to consume data from Apache Kafka with a tumbling event-time window in real-time. We then apply CWT transformation to the data bucketed within this window. The results are fed into a predictive model. The processed dataset, where each device state within a given interval is classified into 6 fault types, is exposed via a web service for use in the analytical dashboard and predictive maintenance reporting. This provides users with fast and granular PV array status updates. However, this use case requires the EMR cluster to run continuously, deployed on EC2 instances or EKS.

### Code execution flow

Let us go through the step necessary to transform the data and apply the classification model:

1. First script `ingest_data.py` is submitted to Spark at EMR. It reads data from Kafka topic for 24 hours of the previous day into PySpark. For this, we use the `startingTimestamp` and `endingTimestamp` consumer parameters to filter the required timestamps. 

2. Next, we apply the Continuous Wavelet Transform (CWT) using the Morlet mother wavelet with a scale of 64, and then stack the 2D scalograms like channels of a color image, making them suitable for feeding into a CNN with LeNet-5 architecture for 64x64 images.

3. Next, we normalize and save the processed data in Parquet format to the S3 silver (staging) bucket.

4. Second script in pipeline `predict_fault.py` loads parquet file, feeds into pre-trained LeNet, gets its prediction classes, appends classes as extra column and stores result in gold S3 bucket. 

The Kafka cluster URIs, names of the silver and gold S3 buckets are obtained from the AWS System Manager Parameter Store.