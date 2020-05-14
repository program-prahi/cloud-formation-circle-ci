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

args = getResolvedOptions(sys.argv, ['JOB_NAME','AWS_REGION','WORKFLOW_ID'])
job.init(args['JOB_NAME'], args)

logger = glueContext.get_logger()

if ('WORKFLOW_ID' not in args or args['WORKFLOW_ID'] is None or args['WORKFLOW_ID'] == ''
    'AWS_REGION' not in args or args['AWS_REGION'] is None or args['AWS_REGION'] == ''): 
    #write out an error message and exit
    logger.error('An input parameter was not passed in correctly')
    missingInput = ''
    if args['WORKFLOW_ID'] is None:
        missingInput = 'WORKFLOW_ID'
    if args['AWS_REGION'] is None:
        missingInput = 'AWS_REGION'
    logger.error('** The input Variable ' + missingInput + ' is not present in the input for Job: ' + args['JOB_NAME'])
    sys.exit(1)

client = boto3.client('glue',region_name=args['AWS_REGION'])
response = client.start_workflow_run(
    Name=args['WORKFLOW_ID']
)
logger.info("Response on starting the Workflow: {}".format(response))