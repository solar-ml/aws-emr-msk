
There are two main components of the solution: data processing and workflow orchestration. AWS offers many services that are well suited for ETL tasks. Each service has its own unique features, strengths and limitations, as well as overlapping functionality. We shall give a brief overview and choose those that fit best in our particular case.  

We will consider between:
- **AWS Glue**, 
- **AWS Data Pipeline**, 
- **Amazon EMR on EC2/EKS** or **Amazon EMR Serverless** with **StepFunctions**,
- **Apache Airflow**. 


That's a good question. AWS provides several tools for big data extract, transform, and load (ETL) processes and analytics, but they have different features and use cases. Here is a brief comparison of AWS Glue vs EMR Serveless vs EMR on EC2/EKS vs AWS Data Pipeline based on the search results¹²³:




Can you compare StepFunctions vs Amazon Managed Workflows for Apache Airflow. Pros and Cons. In a table please | Service | Description | Pros | Cons |

| EMR Serverless | A serverless runtime environment that simplifies running open-source frameworks like Apache Spark, Hive, and Presto at petabyte scale. | - No need to configure, manage, or scale clusters. - Optimized runtimes for Spark and Hive. - Flexible job execution options. - Supports PySpark and TensorFlow. | - Still in preview mode. - May not support all features of EMR on EC2/EKS/Outpost. - Less control over cluster configuration and management than EMR on EC2/EKS/Outpost. |

EMR Serverless provides a serverless runtime environment that simplifies the operation of analytics applications such as Apache Spark and Apache Hive. With EMR Serverless, you don’t have to configure, optimize, secure, or operate clusters to run applications with these frameworks.

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
![](img/Arch_Amazon-EMR_64.png)

| AWS Glue | EMR Serverless |
| --- | --- |
| Designed for ETL processes and data integration | Designed for data processing and analytics |

EMR services are more appropriate for analytics applications that require high performance processing using open source tools. Since our task is a fairly short-term conversion, continuous operation of the EMR cluster is not financially viable.

Running EMR Serverless can be less expensive and faster than creating and terminating EMR clusters programmatically with AWS CLI or StepFunctions, especially for short-lived and sporadic computing tasks. This is due to the following reasons:

1. Pay-per-use pricing: With EMR Serverless, you only pay for the resources used during job execution, making it cost-efficient for infrequent or unpredictable workloads. You are not billed for idle time between jobs.

2. Resource allocation and scaling: EMR Serverless automatically scales resources based on workload, ensuring you only pay for what you need. In contrast, with EMR on EC2, you may need to over-provision resources to handle peak workloads or under-provision resources during off-peak periods.
