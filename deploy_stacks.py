import boto3
import base64
from botocore.exceptions import ClientError
from ast import literal_eval
import json
import os
import time


def create_role(rolename):
    client = boto3.client('iam')
    assume_policy_document = json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "dms.amazonaws.com"
                },
                    "Action": "sts:AssumeRole"
                }
            ]
            })
    response = client.create_role(RoleName=rolename, AssumeRolePolicyDocument=assume_policy_document)
    print(response)
    if rolename == "dms-cloudwatch-logs-role":
        response = client.attach_role_policy(RoleName=rolename, PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonDMSCloudWatchLogsRole')
        print(response)
    if rolename == "dms-vpc-role":
        response = client.attach_role_policy(RoleName=rolename, PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonDMSVPCManagementRole')
        print(response)


def get_secret():
    secret_name = os.environ["AWS_SECRET_NAME"]
    region_name = os.environ["AWS_SECRET_REGION"]
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])         
    return secret


def list_stacks():
    stack_name = os.environ["STACK_NAME"]
    stack_names = list()
    cf_client = boto3.client('cloudformation')
    response = cf_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE','UPDATE_COMPLETE'])
    for i in response['StackSummaries']:
        stack_names.append(i['StackName'])
    if stack_name in stack_names:
        update_stack()
    else:
        create_stack()


def describe_stacks():
    stack_name = os.environ["STACK_NAME"]
    errors = ['CREATE_FAILED','ROLLBACK_IN_PROGRESS','ROLLBACK_FAILED','ROLLBACK_COMPLETE']
    cf_client = boto3.client('cloudformation')
    response = cf_client.describe_stacks(StackName=stack_name)
    time.sleep(10)
    if response['Stacks'][0]['StackStatus'] == 'CREATE_IN_PROGRESS':
        print(response['Stacks'][0]['StackStatus'])
        describe_stacks()
    elif response['Stacks'][0]['StackStatus'] == 'CREATE_COMPLETE':
        exit(0)
    elif response['Stacks'][0]['StackStatus'] in errors:
        exit(254) 

def update_stack():
    stack_name = os.environ["STACK_NAME"]
    print("update_stack")
    cf_client = boto3.client('cloudformation')
    templateurl = "https://"+os.environ['SYNC_BUCKET_NAME']+".s3.amazonaws.com/datalake.yaml"
    parameters = open("parameters.json",'r')
    parameters_json = json.load(parameters)
    parameters.close()
    try:
        response = cf_client.update_stack(
            StackName=stack_name,
            TemplateURL=templateurl,
            Capabilities=['CAPABILITY_IAM','CAPABILITY_NAMED_IAM'],
            Parameters=parameters_json)
    except ClientError as e:
        print(e.response['Error']['Message'])
        exit(254)
    describe_stacks()


def create_stack():
    stack_name = os.environ["STACK_NAME"]
    cf_client = boto3.client('cloudformation')
    templateurl = "https://"+os.environ['SYNC_BUCKET_NAME']+".s3.amazonaws.com/datalake.yaml"
    parameters = open("parameters.json",'r')
    parameters_json = json.load(parameters)
    parameters.close()
    try:
        response = cf_client.create_stack(
            StackName=stack_name,
            TemplateURL=templateurl,
            Capabilities=['CAPABILITY_IAM','CAPABILITY_NAMED_IAM'],
            Parameters=parameters_json)
    except ClientError as e:
        print(e.response['Error']['Message'])
        exit(254)        
    print("create_stack")
    describe_stacks()

if __name__ == '__main__':
    secret_value = get_secret() # Get the DB Credetionals from secret
    secret_value = literal_eval(secret_value)
    parameters = open("parameters.json", 'r')
    parameters_json = json.load(parameters)
    parameters.close()
    # Placing the DB credentials in the parameters.json file
    for i in range(0, len(parameters_json)):
        if parameters_json[i]["ParameterKey"] == "DBName":
            parameters_json[i]["ParameterValue"] = secret_value["DBName"]
        if parameters_json[i]["ParameterKey"] == "Password":
            parameters_json[i]["ParameterValue"] = secret_value["Password"]
        if parameters_json[i]["ParameterKey"] == "Username":
            parameters_json[i]["ParameterValue"] = secret_value["Username"]
        if parameters_json[i]["ParameterKey"] == "Host":
            parameters_json[i]["ParameterValue"] = secret_value["Host"]
        if parameters_json[i]["ParameterKey"] == "CodaS3BucketName":
            parameters_json[i]["ParameterValue"] = os.environ["SYNC_BUCKET_NAME"]
    parameters = open("parameters.json", 'w')
    json.dump(parameters_json, parameters)
    parameters.close()
    # Checking DMS Cloudwatch role and DMS Vpc role are present in the account else creating the roles.
    client = boto3.client('iam')
    try:
        cw_role = client.get_role(RoleName='dms-cloudwatch-logs-role')
    except client.exceptions.NoSuchEntityException as e:
        create_role("dms-cloudwatch-logs-role")
    try:
        cw_role = client.get_role(RoleName='dms-vpc-role')
    except client.exceptions.NoSuchEntityException as e:
        create_role("dms-vpc-role")
    # Deploying stacks
    list_stacks()   