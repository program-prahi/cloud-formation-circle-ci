######################################################################################################
#
#   Company Name:   Fluent - ETL
#   Created By:     Prahathish Kameswaran - Coda Global
#       
#   Description:    ETL that exports CDC files in RawZone to TransientZone
#
#   Input parameters requrired: 
#   input_database, input_table, output_bucket, output_path
#
#    Example: 
# # Configuration Variables - Crawler Catalog
#   input_database = "fluent_dev_kinesis_delivery_database"
#   input_table = "fluent_dev_cdc_table"
#   output_bucket = "fluent-dev-datalake-transient-dev-394780878318"
#   output_path = "FILU"
#   operation = "insert"
#
#######################################################################################################
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame 
from awsglue.transforms import Relationalize
from awsglue.job import Job
from pyspark.sql.types import StructType,StringType,StructField,LongType,DoubleType,BooleanType
from pyspark.sql.functions import from_json
import datetime
import boto3

#Create Glue Context and Spark Session
glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session

logger = glueContext.get_logger()
job = Job(glueContext)
# Configuration Variables - Crawler Catalog
input_database = None
input_table = None

# Clear files in Output bucket
output_bucket = None
output_path = None
operation = None
file_filter = "run"

       
##Input Attributes
args = getResolvedOptions(sys.argv,
                          ['JOB_NAME',
                          'TempDir',
                          'input_database',
                          'input_table',
                          'output_bucket',
                          'output_path',
                          'operation'])
job.init(args['JOB_NAME'], args)

if ('input_database' not in args or 'input_table' not in args or 'output_bucket' not in args or 'output_path' not in args or 'operation' not in args
    or args['input_database'] is None or args['input_table'] is None or args['output_bucket'] is None or args['output_path'] is None or args['operation'] is None
    or args['input_database'] == '' or args['input_table'] == '' or args['output_bucket'] == '' or args['output_path'] == '' or args['operation'] == ''): 
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
    if args['operation'] is None:
        missingInput = 'operation'
    logger.error('** The input Variable ' + missingInput + ' is not present in the input for Job: ' + args['JOB_NAME'])
    sys.exit(1)

else: 
    input_database = args['input_database']
    input_table = args['input_table']
    output_bucket = args['output_bucket']   
    output_path = args['output_path']
    operation = args['operation']

s3 = boto3.resource('s3')
bucket = s3.Bucket(output_bucket)

now = datetime.datetime.utcnow()
for obj in bucket.objects.filter(Prefix=output_path + "/" + file_filter):
    s3.Object(bucket.name, obj.key).delete()

tbl_cdc_dyf = glueContext.create_dynamic_frame_from_catalog(database=input_database, table_name=input_table,format="parquet",transformation_ctx = input_table).select_fields(["data","metadata"])
tbl_cdc_df = tbl_cdc_dyf.toDF()

if(len(tbl_cdc_df.take(1)) == 0):
    logger.info("No " + operation + " to perform for Today: " + now.strftime("%Y-%m-%d %H:%M:%S") + "(UTC)")

else:
    meta_data_schema = StructType([StructField("operation",StringType(),True),StructField("partition-key-type",StringType(),True), \
                                    StructField("record-type",StringType(),True),StructField("schema-name",StringType(),True), \
                                    StructField("table-name",StringType(),True),StructField("timestamp",StringType(),True),StructField("transaction-id",StringType(),True)])

    ## Extracting Metadata from the CDC Records (Inserts Only)
    metadataDf =  tbl_cdc_df.withColumn("metadataTemp",from_json("metadata",meta_data_schema))  \
                                    .select("data","metadataTemp") \
                                    .filter("metadataTemp.`operation` = '"+ operation + "'")

    ## Table Frequency of each Table incoming in Change Data Capture
    metadataDf.printSchema()
    metadataDf.createOrReplaceTempView("cdc_table")
    table_occurence_query = "select metadataTemp.`table-name` as table_name from cdc_table group by table_name order by COUNT(1)"
    table_list  = spark.sql(table_occurence_query).select("table_name").rdd.flatMap(lambda r: r).collect()
    logger.info('Delta (CDC) Tables List' + str(table_list))

    ## Schemas of Tables for FILU Database: ##  Add Additional Table Schemas here
    tableSchemaMappings = {
        "T_BaseID": StructType([StructField("bid",LongType(),True),StructField("emailcrc",LongType(),True),StructField("emailmd5",StringType(),True), \
                                    StructField("shade",LongType(),True),StructField("email",StringType(),True)]),

        "T_Demographic":  StructType([StructField("bid",StringType(),True),StructField("date",StringType(),True),StructField("version",LongType(),True), \
                                        StructField("lastmodified",StringType(),True),StructField("lastsurveymodified",StringType(),True), \
                                        StructField("email",StringType(),True),StructField("firstname",StringType(),True), \
                                        StructField("lastname",StringType(),True),StructField("address1",StringType(),True), \
                                        StructField("address2",StringType(),True),StructField("city",StringType(),True), \
                                        StructField("state",StringType(),True),StructField("zippost",StringType(),True), \
                                        StructField("gender",StringType(),True),StructField("phone",StringType(),True), \
                                        StructField("dobyear",StringType(),True),StructField("dobmonth",StringType(),True), \
                                        StructField("dobday",StringType(),True),StructField("bvemail",StringType(),True), \
                                        StructField("bvphone",StringType(),True),StructField("bvaddress",StringType(),True), \
                                        StructField("clientip",StringType(),True),StructField("ispid",StringType(),True), \
                                        StructField("carrierid",StringType(),True),StructField("zipplus4",StringType(),True)]),   
                                                                            
        "T_Demographic_Survey": StructType([StructField("bid",StringType(),True),StructField("aid",StringType(),True),StructField("vid",StringType(),True), \
                                    StructField("surveydate",StringType(),True),StructField("lastsurveydate",StringType(),True)]),

        "T_Demographic_Survey_Attribute" : StructType([StructField("aid",StringType(),True),StructField("attribute",StringType(),True)]),
                                    
        "T_Demographic_Survey_Value": StructType([StructField("vid",StringType(),True),StructField("value",StringType(),True)]),

        "T_Demographic_Tag": StructType([StructField("bid",StringType(),True),StructField("tagaid",StringType(),True), \
                                StructField("tagvid",StringType(),True), StructField("tagdate",StringType(),True)]),

        "T_Demographic_Tag_Attribute": StructType([StructField("tagaid",StringType(),True),StructField("attribute",StringType(),True), \
                                        StructField("note",StringType(),True),StructField("apikey",StringType(),True)]),

        "T_Demographic_Tag_Value":  StructType([StructField("tagvid",StringType(),True),StructField("value",StringType(),True)]),

        "T_Subscribed_Offer": StructType([StructField("id",StringType(),True),StructField("bid",StringType(),True), \
                                StructField("campaignid",StringType(),True),StructField("solddate",StringType(),True), \
                                StructField("deliverystepid",StringType(),True),StructField("revenue",StringType(),True)]),
        
        "T_Visited_Affiliate":  StructType([StructField("id",StringType(),True),StructField("bid",StringType(),True),StructField("affiliateid",StringType(),True), \
                                    StructField("subaff2",StringType(),True),StructField("date",StringType(),True),StructField("period",StringType(),True)]),   
    }
    #Casting Non-String Columns as Kinesis Sends Record Values as String Sometimes
    table_cast_columns = {
        
        "T_BaseID": {"bid":LongType(),"emailcrc":LongType(), "shade":LongType()},
        
        "T_Demographic": {"bid":LongType(),"version":LongType(), \
                            "gender":BooleanType(), "dobyear":LongType(),"dobmonth":LongType(), \
                            "dobday":LongType(),"bvemail":BooleanType(), \
                            "bvaddress":BooleanType(), "ispid":LongType(), \
                            "carrierid":LongType(),"zipplus4":LongType()},
        
        "T_Demographic_Survey": {"bid":LongType(),"aid":LongType(),"vid":LongType()},
        
        "T_Demographic_Survey_Attribute": {"aid":LongType()},
        
        "T_Demographic_Survey_Value":{"vid":LongType()},
        
        "T_Demographic_Tag": {"bid":LongType(), "tagaid":LongType(), "tagvid":LongType()},
        
        "T_Demographic_Tag_Attribute": {"tagaid":LongType()},
        
        "T_Demographic_Tag_Value": {"tagvid":LongType()},
        
        "T_Subscribed_Offer":{"id":LongType(),"bid":LongType(),"campaignid":LongType(), \
                                "deliverystepid":LongType(),"revenue":DoubleType()},
                                
        "T_Visited_Affiliate": {"id":LongType(),"bid":LongType(),"affiliateid":LongType(),"period":LongType()}
    }

    ## Filer only allowed tables
    updated_table_list = list(set(table_list) - set([key for key in table_list if key not in tableSchemaMappings.keys()]))
    logger.info('Updated Table List'+ str(updated_table_list))

    ## Writing Change Data Capture Table to Transient Zone
    for table_name in updated_table_list:
        # if table_name == "T_Demographic_Tag":
        dataTempTable =  metadataDf.filter("metadataTemp.`table-name` = '" + table_name + "'")
        dataTable = dataTempTable.withColumn("dataTemp",from_json("data",tableSchemaMappings[table_name])).select("dataTemp.*")
        cast_columns = table_cast_columns[table_name]
        for column in cast_columns.keys():
            dataTable = dataTable.withColumn(column, dataTable[column].cast(cast_columns[column]))
        output_dir = "s3://" + output_bucket + "/" + output_path + "/" + table_name.lower() + "/"
        dynamic_frame_name = table_name
        if operation == 'update':
            dynamic_frame_name = table_name + "_cdc_update"
            output_dir = "s3://" + output_bucket + "/" + output_path + "/" + dynamic_frame_name.lower() +"/"
        connectionOptions = {"path": output_dir}
        data_table_dyf = DynamicFrame.fromDF(dataTable,glueContext,dynamic_frame_name)
        logger.info('Inserting ' + table_name + 'to Transient Zone Path: ' + output_dir )
        glueContext.write_dynamic_frame_from_options(frame=data_table_dyf, connection_type = "s3", connection_options = connectionOptions, \
                                                        format="parquet", transformation_ctx = "export_raw_cdc_" + table_name + "_to_frame")

    logger.info('** The job ' + args['JOB_NAME'] + ' was successful')
    job.commit()