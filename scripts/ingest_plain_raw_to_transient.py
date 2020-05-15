######################################################################################################
#
#   Company Name:   Fluent - ETL
#   Created By:     Prahathish Kameswaran - Coda Global
#       
#   Description:    ETL that exports CSV Files in S3 Raw Zone to Parquet Files in Transient Zone
#
#   Input parameters requrired: 
#   input_database, input_table, output_bucket, output_path
#
#    Example: 
# # Configuration Variables - Crawler Catalog
#   input_database = "fluent_dev_filu_db_raw_dev"
#   input_table = "t_demographic"
#
# # Clear files in Output bucket
#   output_bucket = "fluent-dev-datalake-transient-dev-394780878318"
#   output_path = "FILU"
#
#######################################################################################################
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
import boto3

# Create AWS Glue Context
glueContext = GlueContext(SparkContext.getOrCreate())
logger = glueContext.get_logger()

# Configuration Variables - Crawler Catalog
input_database = None
input_table = None

# Clear files in Output bucket
output_bucket = None
output_path = None
file_filter = "run"

logger = glueContext.get_logger()

args = getResolvedOptions(sys.argv,
                          ['JOB_NAME',
                          'input_database',
                          'input_table',
                          'output_bucket',
                          'output_path'])

if ('input_database' not in args or 'input_table' not in args or 'output_bucket' not in args or 'output_path' not in args
    or args['input_database'] is None or args['input_table'] is None or args['output_bucket'] is None or args['output_path'] is None 
    or args['input_database'] == '' or args['input_table'] == '' or args['output_bucket'] == '' or args['output_path'] == ''): 
    #write out an error message and exit
    logger.error('An input parameter was not passed in correctly')
    missingInput = ''
    if args['input_database'] is None:
        missingInput = 'input_database'
    if args['input_table'] is None: 
        missingInput = 'input_table'
    if args['output_bucket'] is None:
        missingInput = 'output_bucket'
    if args['output_path'] is None:
        missingInput = 'output_path'
    logger.error('** The input Variable ' + missingInput + ' is not present in the input for Job: ' + args['JOB_NAME'])
    sys.exit(1)

else: 
    input_database = args['input_database']
    input_table = args['input_table']
    output_bucket = args['output_bucket']   
    output_path = args['output_path']

    # Configuration Variables - S3 - Export Folder
    output_dir = "s3://" + output_bucket + "/" + output_path + "/" + input_table

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(output_bucket)

    for obj in bucket.objects.filter(Prefix=output_path + "/" + file_filter):
        s3.Object(bucket.name, obj.key).delete()

    # Load up the CSV Files for conversion
    tbl_orgs = glueContext.create_dynamic_frame_from_catalog(database=input_database, table_name=input_table)

    # Export CSV Files as Parquet Files
    export_frame_to_file = glueContext.write_dynamic_frame_from_options(frame = tbl_orgs, connection_type = "s3", connection_options = {"path": output_dir}, format = "parquet", transformation_ctx = "export_raw_to_transient")
        
    logger.info('** The job ' + args['JOB_NAME'] + ' was successful')