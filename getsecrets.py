import boto3
import base64
from botocore.exceptions import ClientError
from ast import literal_eval
import json
import os


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
    stack_names = list()
    cf_client = boto3.client('cloudformation')
    response = cf_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE','UPDATE_COMPLETE'])
    for i in response['StackSummaries']:
        stack_names.append(i['StackName'])
    if "test-circleci-stack" in stack_names:
        update_stack()
    else:
        create_stack()


def update_stack():
    print("update_stack")
    cf_client = boto3.client('cloudformation')
    templateurl = "https://"+os.environ['SYNC_BUCKET_NAME']+".s3.amazonaws.com/bucket.yaml"
    parameters = open("parameters.json",'r')
    parameters_json = json.load(parameters)
    parameters.close()
    try:
        response = cf_client.update_stack(
            StackName='test-circleci-stack',
            TemplateURL=templateurl,
            Parameters=parameters_json)
    except ClientError as e:
        print(e.response['Error']['Message'])
        exit(254)
        


def create_stack():
    cf_client = boto3.client('cloudformation')
    templateurl = "https://"+os.environ['SYNC_BUCKET_NAME']+".s3.amazonaws.com/bucket.yaml"
    parameters = open("parameters.json",'r')
    parameters_json = json.load(parameters)
    parameters.close()
    try:
        response = cf_client.create_stack(
            StackName='test-circleci-stack',
            TemplateURL=templateurl,
            Parameters=parameters_json)
    except ClientError as e:
        print(e.response['Error']['Message'])
        exit(254)        
    print("create_stack")

if __name__ == '__main__':
    secret_value = get_secret()
    secret_value = literal_eval(secret_value)
    parameters = open("parameters.json", 'r')
    parameters_json = json.load(parameters)
    parameters.close()
    for i in range(0, len(parameters_json)):
        if parameters_json[i]["ParameterKey"] == "DBName":
            parameters_json[i]["ParameterValue"] = secret_value["DBName"]
        if parameters_json[i]["ParameterKey"] == "DBPassword":
            parameters_json[i]["ParameterValue"] = secret_value["Password"]
    parameters = open("parameters.json", 'w')
    json.dump(parameters_json, parameters)
    parameters.close()
    # list_stacks()    