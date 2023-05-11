
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



## Orchestration approach consideration

The central piece of the workflow is the **AWS StepFunctions** state machine. It orchestrates two Spark jobs and handle failures and retries. Its execution is triggered by the event scheduled in the **EventBridge**.


### AWS Data Pipeline with EMR Serverless
![](aws_data_pipeline.drawio.svg)


### The state machine shown below consists of 10 states, each performing a specific task or decision.

![](stepfunctions_graph.svg)

- `IngestData` **task** state triggers a Lambda function [`ingest_data`](<src/lambda/ingest_data_lambda.py>) which is responsible for running the `ingest_data.py` script from S3 `bootstrap` bucket on an EMR Serverless cluster to obtain data from a Kafka cluster. The function takes care of submitting the EMR job and returns the `job_id` for use downstream. If the function encounters an error, it will retry up to 6 times with an exponential backoff strategy. If all retries fail, it moves to the `NotifyFailure` state.

- `WaitForIngestData` **wait** state pauses the state machine for the specified number of seconds in `$.wait_time` before moving to the next state. `$.wait_time` is passed as input parameter to the StepFunction by EventBridge script. This wait time is used to avoid polling the EMR job status too frequently. 

- `GetIngestDataStatus` **task** state triggers a Lambda function `get_ingest_data_status` to retrieve the status of an EMR job by calling `get_job_run` method on the EMR Serverless client and passing job ID. If the function encounters an error, it will retry up to 6 times with an exponential backoff strategy. If all retries fail, it moves to the `NotifyFailure` state.

- `CheckIngestDataStatus` **choice** state evaluates the status of data ingestion. If it has succeeded, it moves to the `PredictFault` state. If it has failed, it moves to the `NotifyFailure` state. If the status is unknown, it moves back to the `WaitForIngestData` state.

- `PredictFault`, `WaitForPredictFault`, `GetPredictFaultStatus`, `CheckPredictFaultStatus` states repeat the same pattern as the 4 steps above, including submitting the second Spark job `predict_fault.py` to EMR Serverless via lambda function call and monitoring its execution state.

- `NotifySuccess` **task** state triggers a Lambda function `notify_success` to send a notification about the successful completion of the Spark jobs. 

- `NotifyFailure` **task** state triggers a Lambda function `notify_failure` to send a notification about the **failure of any of the previous steps**. 

#### Advantages of using the StepFunctions approach:

- **Error handling**: Errors are managed at each Task state, providing a robust way to handle failures.
- **Retries**: Failed Lambda functions are retried with an exponential backoff strategy, reducing the impact of transient errors.
- **Status monitoring**: Continuous checks of Spark job statuses are performed, with appropriate actions taken based on each job's status.
- **Orchestration**: Step Functions simplify complex workflow management by breaking them into smaller, more manageable states.
- **Modularity**: With each state in the workflow having a specific purpose, the overall process becomes easier to understand.
- **Scalability and cost-effectiveness**: The service scales automatically with workload, charging only for what you use, making it a cost-effective choice for managing workflows




### Further conversion to streaming application

Imagine the requirement change and fault detection is 

client you are sell products globally and want to understand the relationship between the time of day and buying patterns in different geographic regions in real-time. For any given window of time — this 15-minute period, this hour, this day, or this week— you want to know the current sales volumes by country. You are not reviewing previous sales periods or examing running sales totals, but real-time sales during a sliding time window.

We may also convert this pipeline to near real-time streaming application. 

We will switch from batch to streaming — from `read()` to `readstream()` and from `write()` to `writestream()`

From Amazon MSK the data is ingested into Amazon EMR (Amazon Elastic MapReduce), a Spark/Hadoop/Hive cluster deployed on AWS. For this particular task, we chose a 24-hour batch window. So data is consumed from 0:00 to 23:59:59 the day before the current day. This window can be adjusted and predictive model can be applied more frequently to narrower ranges of data. However, this will incur additional charges from EMR.



Moreover, while we handle batch processing with EMR Serverless within this pipeline it can also be converted into a near real-time streaming application. To achieve this, we can use Spark Structured Streaming to consume data from Apache Kafka with a tumbling event-time window in real-time. We then apply CWT transformation to the data bucketed within this window. The results are fed into a predictive model. The processed dataset, where each device state within a given interval is classified into 6 fault types, is exposed via a web service for use in the analytical dashboard and predictive maintenance reporting. This provides users with fast and granular PV array status updates. However, this use case requires the EMR cluster to run continuously, deployed on EC2 instances or EKS.

### Code execution flow

Let us go through the step necessary to transform the data and apply the classification model:

1. First script `ingest_data.py` is submitted to Spark at EMR. It reads data from Kafka topic for 24 hours of the previous day into PySpark. For this, we use the `startingTimestamp` and `endingTimestamp` consumer parameters to filter the required timestamps. 

2. Next, we apply the Continuous Wavelet Transform (CWT) using the Morlet mother wavelet with a scale of 64, and then stack the 2D scalograms like channels of a color image, making them suitable for feeding into a CNN with LeNet-5 architecture for 64x64 images.

3. Next, we normalize and save the processed data in Parquet format to the S3 silver (staging) bucket.

4. Second script in pipeline `predict_fault.py` loads parquet file, feeds into pre-trained LeNet, gets its prediction classes, appends classes as extra column and stores result in gold S3 bucket. 

The Kafka cluster URIs, names of the silver and gold S3 buckets are obtained from the AWS System Manager Parameter Store.



SSM PARAMS

kafka-servers
kafka-topics
sns-topic
log-bucket
silver-bucket
gold-bucket
emr-app-id