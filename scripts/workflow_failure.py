######################################################################################################
#
#   Company Name:   s3 - ETL
#   Created By:     Prahathish Kameswaran
#       
#   Description:    Sends a SNS Notification that there is a Failure in Workflow operation
#
#   Input parameters requrired: 
#   AWS_REGION,sns_arn
#
#    Example: 
#      AWS_REGION = 'us-east-1'
#      sns_arn = 'arn:aws:sns:us-east-1:394780878318:dev-datalake-dev-sns-workflow-topic'
#
#######################################################################################################
# Libraries Configurations Section
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import boto3
import json
import datetime
from awsglue.utils import getResolvedOptions

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)


args = getResolvedOptions(sys.argv, ['JOB_NAME','AWS_REGION','sns_arn'])

job.init(args['JOB_NAME'], args)

logger = glueContext.get_logger()

if ('sns_arn' not in args or args['sns_arn'] is None or args['sns_arn'] == ''
    'AWS_REGION' not in args or args['AWS_REGION'] is None or args['AWS_REGION'] == ''): 
    #write out an error message and exit
    logger.error('An input parameter was not passed in correctly')
    missingInput = ''
    if args['sns_arn'] is None:
        missingInput = 'sns_arn'
    if args['AWS_REGION'] is None:
        missingInput = 'AWS_REGION'
    logger.error('** The input Variable ' + missingInput + ' is not present in the input for Job: ' + args['JOB_NAME'])
    sys.exit(1)
## @params: [JOB_NAME]

# lambda_client = boto3.client('lambda', region_name = args['AWS_REGION'])  ## Step-3
subject = "Workflow Notification"
now = datetime.datetime.utcnow()
message = {
  "type": "error",
  "message": "There was an Error Processing data for today: " + now.strftime("%Y-%m-%d %H:%M:%S") + "(UTC)",
  "code": "500"
}
target_arn = args['sns_arn']
region = args['AWS_REGION']
sns_client = boto3.client('sns',region_name=region)
response = sns_client.publish(
                TargetArn=target_arn,
                Message=json.dumps({"default": json.dumps(message,indent=4,sort_keys=True)}),
                Subject=subject,
                MessageStructure='json'
            )
logger.info("response {}".format(response))

