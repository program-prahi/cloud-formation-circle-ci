import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame 
from awsglue.transforms import Relationalize
from awsglue.job import Job
from pyspark.sql.types import StructType,StringType,StructField,LongType,DoubleType,BooleanType
from pyspark.sql.functions import from_json
import boto3

#Create Glue Context and Spark Session
glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session

logger = glueContext.get_logger()

# Configuration Variables - Crawler Catalog
input_database = None
input_table = None

# Clear files in Output bucket
output_bucket = None
output_path = None
file_filter = "run"

def get_relationalized_table(dynamic_frame,table_name,staging_path_dir):
    relationalize_frame_collection = Relationalize.apply(frame=dynamic_frame,staging_path=staging_path_dir,transformation_ctx = "Relationalize:" + table_name)
    for dyf_name in relationalize_frame_collection.keys():
        return relationalize_frame_collection.select(dyf_name)
       
##Input Attributes
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

s3 = boto3.resource('s3')
bucket = s3.Bucket(output_bucket)

for obj in bucket.objects.filter(Prefix=output_path + "/" + file_filter):
    s3.Object(bucket.name, obj.key).delete()

relationalize_temp_dir = "s3://aws-glue-temporary-394780878318-us-east-1/temp-dir/"

tbl_cdc_dyf = glueContext.create_dynamic_frame_from_catalog(database=input_database, table_name=input_table,format="parquet").select_fields(["data","metadata"])
meta_data_schema = StructType([StructField("operation",StringType(),True),StructField("partition-key-type",StringType(),True), \
                                StructField("record-type",StringType(),True),StructField("schema-name",StringType(),True), \
                                StructField("table-name",StringType(),True),StructField("timestamp",StringType(),True),StructField("transaction-id",StringType(),True)])

## Extracting Metadata from the CDC Records (Inserts Only)
metadataDf =  tbl_cdc_dyf.toDF().withColumn("metadataTemp",from_json("metadata",meta_data_schema)).select("data","metadataTemp").filter("metadataTemp.`operation` = 'insert'")
tbl_cdc_transformed = DynamicFrame.fromDF(metadataDf,glueContext,input_table)

## Table Occurence incoming in Change Data Capture
tbl_cdc_transformed.printSchema()
tbl_cdc_transformed.toDF().createOrReplaceTempView("cdc_table")
table_occurence_query = "select metadataTemp.`table-name` as table_name from cdc_table group by table_name order by COUNT(1)"
table_list  = spark.sql(table_occurence_query).select("table_name").rdd.flatMap(lambda r: r).collect()
logger.info('Delta (CDC) Tables List' + str(table_list))

## Schemas of Tables for FILU Database: ##  Add Additional Table Schemas here
tableSchemaMappings = {
    "T_BaseID": StructType([StructField("bid",LongType(),True),StructField("emailcrc",LongType(),True),StructField("emailmd5",StringType(),True), \
                                StructField("shade",LongType(),True),StructField("email",StringType(),True)]),

    "T_Demographic":  StructType([StructField("bid",LongType(),True),StructField("date",StringType(),True),StructField("version",LongType(),True), \
                                    StructField("lastmodified",StringType(),True),StructField("lastsurveymodified",StringType(),True), \
                                    StructField("email",StringType(),True),StructField("firstname",StringType(),True), \
                                    StructField("lastname",StringType(),True),StructField("address1",StringType(),True), \
                                    StructField("address2",StringType(),True),StructField("city",StringType(),True), \
                                    StructField("state",StringType(),True),StructField("zippost",StringType(),True), \
                                    StructField("gender",BooleanType(),True),StructField("phone",LongType(),True), \
                                    StructField("dobyear",LongType(),True),StructField("dobmonth",LongType(),True), \
                                    StructField("dobday",LongType(),True),StructField("bvemail",BooleanType(),True), \
                                    StructField("bvphone",StringType(),True),StructField("bvaddress",BooleanType(),True), \
                                    StructField("clientip",StringType(),True),StructField("ispid",LongType(),True), \
                                    StructField("carrierid",StringType(),True),StructField("zipplus4",LongType(),True)]),   
                                                                         
    "T_Demographic_Survey": StructType([StructField("bid",LongType(),True),StructField("aid",LongType(),True),StructField("vid",LongType(),True), \
                                StructField("surveydate",StringType(),True),StructField("lastsurveydate",StringType(),True)]),

     "T_Demographic_Survey_Attribute" : StructType([StructField("aid",LongType(),True),StructField("attribute",StringType(),True)]),
                                
    "T_Demographic_Survey_Value": StructType([StructField("vid",LongType(),True),StructField("value",StringType(),True)]),

    "T_Demographic_Tag": StructType([StructField("bid",LongType(),True),StructField("tagaid",LongType(),True), \
                            StructField("tagvid",LongType(),True), StructField("tagdate",StringType(),True)]),

    "T_Demographic_Tag_Attribute": StructType([StructField("tagaid",LongType(),True),StructField("attribute",StringType(),True), \
                                    StructField("note",StringType(),True),StructField("apikey",StringType(),True)]),

    "T_Demographic_Tag_Value":  StructType([StructField("tagvid",LongType(),True),StructField("value",StringType(),True)]),

    "T_Subscribed_Offer": StructType([StructField("id",LongType(),True),StructField("bid",LongType(),True), \
                            StructField("campaignid",LongType(),True),StructField("solddate",StringType(),True), \
                            StructField("deliverystepid",LongType(),True),StructField("revenue",DoubleType(),True)]),
    
    "T_Visited_Affiliate":  StructType([StructField("id",LongType(),True),StructField("bid",LongType(),True),StructField("affiliateid",LongType(),True), \
                                StructField("subaff2",StringType(),True),StructField("date",StringType(),True),StructField("period",LongType(),True)]),   
}

## Filer only allowed tables
updated_table_list = list(set(table_list) - set([key for key in table_list if key not in tableSchemaMappings.keys()]))
logger.info('Updated Table List'+ str(updated_table_list))

## Writing Change Data Capture Table to Transient Zone
for table_name in updated_table_list:
    # if table_name == "T_Demographic_Tag":
    dataTempTable =  tbl_cdc_transformed.toDF().filter("metadataTemp.`table-name` = '" + table_name + "'")
    dataTable = dataTempTable.withColumn("dataTemp",from_json("data",tableSchemaMappings[table_name])).select("dataTemp.*")
    data_table_dyf = DynamicFrame.fromDF(dataTable,glueContext,table_name)
    output_data_dyf = get_relationalized_table(data_table_dyf,table_name,relationalize_temp_dir)
    output_dir = "s3://" + output_bucket + "/" + output_path + "/" + table_name.lower() +"/"
    connectionOptions = {"path": output_dir}
    logger.info('Inserting ' + table_name + 'to Transient Zone Path: ' + output_dir )
    glueContext.write_dynamic_frame_from_options(frame=output_data_dyf, connection_type = "s3", connection_options = connectionOptions, \
                                                    format="parquet", transformation_ctx = "export_raw_cdc_" + table_name + "_to_frame")

logger.info('** The job ' + args['JOB_NAME'] + ' was successful')