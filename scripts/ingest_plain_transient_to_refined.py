######################################################################################################
#
#   Company Name:   Fluent - ETL
#   Created By:     Prahathish Kameswaran - Coda Global
#       
#   Description:    ETL that exports Files in Transient Zone to Refined Zone
#
#   Input parameters requrired: 
#   input_database, input_table, output_bucket, output_path, GLUE_ROLE, first_source
#
#    Example: 
# # Configuration Variables - Crawler Catalog
#   input_database = "fluent_dev_filu_db_transient_dev"
#   input_table = "t_demographic"
#   GLUE_ROLE = "arn:aws:iam::394780878318:role/fluent-role-glueEtlJob"  
#   output_bucket = "fluent-dev-datalake-refined-dev-394780878318"
#   output_path = "FIGAudit/FIG"
#   first_source = "FILU" 
#
#######################################################################################################

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame 
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.sql import functions as F
import datetime
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

first_source = None
glue_role = None

logger = glueContext.get_logger()
job = Job(glueContext)
args = getResolvedOptions(sys.argv,
                          ['JOB_NAME',
                          'input_database',
                          'input_table',
                          'output_bucket',
                          'output_path',
                          'GLUE_ROLE',
                          'first_source'])
job.init(args['JOB_NAME'], args)

if ('input_database' not in args or 'input_table' not in args or 'output_bucket' not in args or 'output_path' not in args
    or 'first_source' not in args or 'GLUE_ROLE' not in args or args['input_database'] is None or args['input_table'] is None
    or args['output_bucket'] is None or args['output_path'] is None or args['first_source'] is None or args['GLUE_ROLE'] is None 
    or args['input_database'] == '' or args['input_table'] == '' or args['output_bucket'] == '' or args['output_path'] == '' 
    or args['first_source'] == '' or args['GLUE_ROLE'] == ''): 
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
    if args['first_source'] is None:
        missingInput = 'first_source'
    if args['GLUE_ROLE'] is None:
        missingInput = 'GLUE_ROLE'
    logger.error('** The input Variable ' + missingInput + ' is not present in the input for Job: ' + args['JOB_NAME'])
    sys.exit(1)

else: 
    input_database = args['input_database']
    input_table = args['input_table']
    output_bucket = args['output_bucket']   
    output_path = args['output_path']
    first_source = args['first_source']
    glue_role = args['GLUE_ROLE']
###################################################
# Create Audit Columns for each Table - 
# created_date : Date
# create_timestamp: timestamp (UTC)
# create_user: string (IAM User created the table)
# first_source: string (Data Source-'FILU')
# create_year: integer (Partioned)
# create_month: integer (Partioned)
# create_date: integer (Partitioned)
###################################################
def create_audit_columns(dataframe):
    frame = dataframe.withColumn("created_date",F.current_date()) \
                     .withColumn("created_timestamp",F.current_timestamp()) \
                     .withColumn("create_user",F.lit(glue_role)) \
                     .withColumn("create_process",F.lit(args['JOB_NAME'])) \
                     .withColumn("first_source",F.lit(first_source)) \
                     .withColumn("create_year",F.year(F.col("created_date"))) \
                     .withColumn("create_month",F.month(F.col("created_date"))) \
                     .withColumn("create_date",F.dayofmonth(F.col("created_date")))
    return frame
# Configuration Variables - S3 - Export Folder
output_dir = "s3://" + output_bucket + "/" + output_path + "/" + input_table
partition_keys = ["create_year","create_month","create_date"]
s3 = boto3.resource('s3')
bucket = s3.Bucket(output_bucket)

for obj in bucket.objects.filter(Prefix=output_path + "/" + file_filter):
    s3.Object(bucket.name, obj.key).delete()

# Load up the Transient Files for conversion
tbl_orgs = glueContext.create_dynamic_frame_from_catalog(database=input_database, table_name=input_table, transformation_ctx=input_table)
# Adding audit columns
now = datetime.datetime.utcnow()
tbl_orgs_df = tbl_orgs.toDF()

if(len(tbl_orgs_df.take(1)) == 0):
    logger.info("No transformation to perform for Today: " + now.strftime("%Y-%m-%d %H:%M:%S") + "(UTC)")

else:
    tbl_audit_df = create_audit_columns(tbl_orgs_df)

    tbl_audit_dyf = DynamicFrame.fromDF(tbl_audit_df,glueContext,input_table)
    
    # Export Transient Files with audit columns as Parquet Files
    export_frame_to_file = glueContext.write_dynamic_frame_from_options(frame = tbl_audit_dyf, connection_type = "s3", connection_options = {"path": output_dir,"partitionKeys": partition_keys}, format = "parquet", transformation_ctx = "export_transient_to_refined")
        
    logger.info('** The job ' + args['JOB_NAME'] + ' was successful')
    job.commit()