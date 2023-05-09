from diagrams import Cluster, Diagram, Edge
from diagrams.aws.analytics import EMR, EMRCluster, ManagedStreamingForKafka
from diagrams.aws.compute import Lambda, LambdaFunction
from diagrams.aws.general import Client, Users
from diagrams.aws.integration import SNS, Eventbridge, StepFunctions
from diagrams.aws.iot import IotFactory, IotSensor
from diagrams.aws.management import SystemsManager
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import (S3, SimpleStorageServiceS3Bucket,
                                  SimpleStorageServiceS3BucketWithObjects)
from diagrams.onprem.queue import Kafka

# with Diagram("Data Pipeline", show=False):
#     with Cluster("AWS"):
#         eventbridge = Eventbridge("EventBridge")
#         lambda1 = Lambda("Ingest_data")
        
#         lambda2 = Lambda("Lambda 2")
#         lambda3 = Lambda("Lambda 3")
#         emr = EMR("EMR Serverless")
#         s3_silver = S3("S3 Silver Bucket")
#         s3_gold = S3("S3 Gold Bucket")
#         apigateway = APIGateway("API Gateway")
#         with Cluster("MSK"):
#             kafka = Kafka("Kafka Cluster")

#     eventbridge >> lambda1 >> emr >> s3_silver
#     s3_silver >> eventbridge >> lambda2 >> emr >> s3_gold
#     s3_gold >> apigateway >> lambda3 >> s3_gold
#     kafka >> emr
    

# with Diagram("Data Pipeline", show=True):  
#     with Cluster("EMR"):
#         emr = EMR("EMR Serverless")
#         s3_silver = SimpleStorageServiceS3Bucket("S3 Silver Bucket")
#         s3_gold = SimpleStorageServiceS3Bucket("S3 Gold Bucket")
#         s3_bootstrap = SimpleStorageServiceS3BucketWithObjects("S3 Bootstrap Bucket")
      
#         with Cluster("Step Functions"):
#             step_func = StepFunctions("Orchestrate state machine")
#             with Cluster("Lambdas"):
#                 with Cluster(""):                    
#                     with Cluster("Step 1"):
#                         lm_ingest_data = LambdaFunction("ingest_data")
#                         lm_get_ingest_data_status = LambdaFunction("ingest_data_status")   
#                     # emr = EMR("EMR Serverless")
#                     with Cluster("Step 2"):
#                         lm_predict_fault = LambdaFunction("predict_fault")
#                         lm_get_predict_fault_status = LambdaFunction("predict_fault_status")

#                 lm_sns = [LambdaFunction("notify_success"), LambdaFunction("notify_failure")]
 

graph_attr = {
    "fontsize": "24",
    "labelloc" : "t",
    "pad": "0.5",
    # "bgcolor": "transparent",
    "beautify": "true"
}

node_attr = {
    "fontsize": "16",
} 
 
with Diagram("Data Pipeline with Amazon EMR Serverless and Amazon MSK", \
    show=True, graph_attr=graph_attr, node_attr=node_attr, direction="LR", \
        filename="aws_data_pipeline"):
    with Cluster("AWS Cloud: region eu-central-1", graph_attr={"fontsize": "20"}):
        emr = EMR("Amazon EMR\nServerless")
        s3_silver = S3("S3 Silver Bucket")
        s3_gold = S3("S3 Gold Bucket")
        s3_bootstrap = S3("S3 Bootstrap\nBucket")
        apigateway = APIGateway("API Gateway")
        
        with Cluster("Step Functions", graph_attr={"fontsize": "18"}):
            step_func = StepFunctions("Orchestrate state machine")
            with Cluster(""):                    
                with Cluster("Step 1", graph_attr={"fontsize": "16"}):
                    lm_ingest_data = LambdaFunction("ingest_data")
                    lm_get_ingest_data_status = LambdaFunction("get_ingest_data_status")   
                with Cluster("Step 2", graph_attr={"fontsize": "16"}):
                    lm_predict_fault = LambdaFunction("predict_fault")
                    lm_get_predict_fault_status = LambdaFunction("get_predict_fault_status")

            lm_success = LambdaFunction("notify_success")
            lm_failure = LambdaFunction("notify_failure")
                    
        eventbridge = Eventbridge("EventBridge")
        sns = SNS("SNS")
        kafka = ManagedStreamingForKafka("Amazon MSK")
        ssm = SystemsManager("SM Parameter Store")
        lm_query_results = LambdaFunction("query_results")
    
    clients = Client("Clients")     
    users = Users("Users")
    scada = IotFactory("SCADA") # Supervisory control and data acquisition (SCADA) 
    
    # data flow >> bold darkgreen edges
    scada >> Edge(color="darkgreen", style="bold") >> kafka >> \
        Edge(color="darkgreen", style="bold") >> \
        lm_ingest_data >> Edge(color="darkgreen", style="bold") >> \
        s3_silver >> Edge(color="darkgreen", style="bold") >> lm_predict_fault >> \
        Edge(color="darkgreen", style="bold") >> s3_gold
        
    # command flow >> darkorange edges
    eventbridge >> Edge(style="bold") >> step_func >> Edge(style="bold") >> \
        lm_ingest_data >> Edge(style="bold") >> lm_get_ingest_data_status >> \
        Edge(style="bold") >> lm_predict_fault >> Edge(style="bold") >> \
        lm_get_predict_fault_status >> Edge(style="bold") >> lm_success # only one path for success
    
    s3_gold >> Edge(color="darkgreen", style="bold") >> \
    lm_query_results >> Edge(color="darkgreen", style="bold") >> \
    apigateway >> Edge(color="darkgreen", style="bold") >> clients
    
    # all other path lead to failure state
    lm_ingest_data >> lm_failure
    lm_get_ingest_data_status >> lm_failure
    lm_predict_fault >> lm_failure  
    lm_get_predict_fault_status >> lm_failure 
        
    s3_bootstrap >> emr # load initial bootstrap scripts
    lm_ingest_data >> Edge(color="darkorange", style="bold") << emr # submit job (step)
    lm_predict_fault >> Edge(color="darkorange", style="bold") << emr # - // -
    
    sns >> users
    # get parameters from System Manager Parameter Store
    lm_ingest_data << ssm
    lm_predict_fault << ssm
    lm_success << ssm
    lm_failure << ssm
    
    # send notifications to SNS
    lm_success >> sns
    lm_failure >> sns
    

    
