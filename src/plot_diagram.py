from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import EMR, EMRCluster, ManagedStreamingForKafka
from diagrams.aws.compute import Lambda, LambdaFunction
from diagrams.aws.general import Client, Users
from diagrams.aws.integration import (SNS, Eventbridge,
                                      SimpleNotificationServiceSnsTopic,
                                      StepFunctions)
from diagrams.aws.iot import IotFactory, IotSensor
from diagrams.aws.management import SystemsManager
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import (S3, SimpleStorageServiceS3Bucket,
                                  SimpleStorageServiceS3BucketWithObjects)
from diagrams.onprem.queue import Kafka

graph_attr = {
    "fontsize": "24",
    "labelloc": "t",
    "pad": "0.5",
    # "bgcolor": "transparent",
    "beautify": "true",
}

node_attr = {
    "fontsize": "14",
}

with Diagram(
    "Data Pipeline with Amazon EMR Serverless and Amazon MSK",
    show=True,
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="LR",
    filename="aws_data_pipeline",
):
    with Cluster("AWS Cloud: region eu-central-1", graph_attr={"fontsize": "20"}):
        with Cluster("VPC-2"):
            emr = EMR("Amazon EMR\nServerless")
            
        s3_silver = S3("S3 Silver Bucket")
        s3_gold = S3("S3 Gold Bucket")
        s3_bootstrap = S3("S3 Bootstrap\nBucket")
        s3_logs = S3("S3 Logs Bucket")
        apigateway = APIGateway("API Gateway")

        with Cluster("Step Functions", graph_attr={"fontsize": "18"}):
            step_func = StepFunctions("State machine")
            with Cluster(""):
                with Cluster("Step 1", graph_attr={"fontsize": "16"}):
                    lm_ingest_data = Lambda("ingest_data")
                    lm_get_ingest_data_status = Lambda("get_ingest_data_status")
                with Cluster("Step 2", graph_attr={"fontsize": "16"}):
                    lm_predict_fault = Lambda("predict_fault")
                    lm_get_predict_fault_status = Lambda("get_predict_fault_status")

            lm_success = Lambda("notify_success")
            lm_failure = Lambda("notify_failure")

        eventbridge = Eventbridge("EventBridge")
        sns = SNS("SNS")
        with Cluster("VPC-1", direction="TB"):
            kafka = ManagedStreamingForKafka("Amazon MSK")
            topic = SimpleNotificationServiceSnsTopic("Topic")
            kafka - topic
        ssm = SystemsManager("SM Parameter Store")
        lm_query_results = Lambda("query_results")

    clients = Client("Clients")
    users = Users("Users")
    scada = IotFactory("SCADA")  # Supervisory control and data acquisition (SCADA)

    # data flow >> bold darkgreen edges
    (
        scada
        >> Edge(color="darkgreen", style="bold")
        >> kafka
        >> Edge(color="darkgreen", style="bold")
        >> lm_ingest_data
        >> Edge(color="darkgreen", style="bold")
        >> s3_silver
        >> Edge(color="darkgreen", style="bold")
        >> lm_predict_fault
        >> Edge(color="darkgreen", style="bold")
        >> s3_gold
    )

    # command flow >> darkorange edges
    (
        eventbridge
        >> Edge(style="bold")
        >> step_func
        >> Edge(style="bold")
        >> lm_ingest_data
        >> Edge(style="bold")
        >> lm_get_ingest_data_status
        >> Edge(style="bold")
        >> lm_predict_fault
        >> Edge(style="bold")
        >> lm_get_predict_fault_status
        >> Edge(style="bold")
        >> lm_success
    )  # only one path for success

    (
        s3_gold
        >> Edge(color="darkgreen", style="bold")
        >> lm_query_results
        >> Edge(color="darkgreen", style="bold")
        >> apigateway
        >> Edge(color="darkgreen", style="bold")
        >> clients
    )

    # all other path lead to failure state
    lm_ingest_data >> lm_failure
    lm_get_ingest_data_status >> lm_failure
    lm_predict_fault >> lm_failure
    lm_get_predict_fault_status >> lm_failure

    s3_bootstrap >> emr  # load initial bootstrap scripts
    # emr << s3_bootstrap
    s3_logs << emr
    lm_ingest_data >> Edge(color="darkorange", style="bold") << emr  # submit job (step)
    lm_predict_fault >> Edge(color="darkorange", style="bold") << emr  # - // -

    sns >> users
    # get parameters from System Manager Parameter Store
    lm_ingest_data - ssm
    lm_get_ingest_data_status - ssm
    lm_predict_fault - ssm
    lm_get_predict_fault_status - ssm
    lm_success - ssm
    lm_failure - ssm
    
    # send notifications to SNS
    lm_success >> sns
    lm_failure >> sns
