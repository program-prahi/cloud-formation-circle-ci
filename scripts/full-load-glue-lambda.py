import boto3
import botocore.exceptions
import json
from datetime import datetime
import os

def modifycdctask(date):
    client = boto3.client('dms')
    replicationtaskarn=os.environ["ReplicationTaskArn"]
    try:
        response = client.start_replication_task(
        ReplicationTaskArn=replicationtaskarn,
        StartReplicationTaskType='start-replication',
        CdcStartPosition=date
        )
    except Exception as e:
        raise e


def lambda_handler(event, context):
    try:
        print(event)
        sns_message = event['Records'][0]['Sns']['Message']
        sns_message=json.loads(sns_message)
        print(sns_message['Event Message'])
        if "FULL_LOAD_ONLY_FINISHED" in sns_message['Event Message']:
            workflowname=os.environ["workflowname"]
            client = boto3.client('glue')
            response = client.start_workflow_run(Name=workflowname)
            timestamp = event['Records'][0]['Sns']['Timestamp']
            d=datetime.strptime(timestamp,"%Y-%m-%dT%H:%M:%S.%fZ")
            d=d.strftime("%Y-%m-%dT%H:%M:%S")
            modifycdctask(d)
    except Exception as e:
        print(e)
