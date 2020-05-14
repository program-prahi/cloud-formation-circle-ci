import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame 
from awsglue.transforms import ResolveChoice,Relationalize
from awsglue.job import Job
from pyspark.sql.types import *
from pyspark.sql import functions as F
import datetime 
import boto3
glueContext = GlueContext(SparkContext.getOrCreate())
spark = glueContext.spark_session
logger = glueContext.get_logger()
job = Job(glueContext)

# fuzzy_match_database = "fluent_dev_filu_db_transient_dev"
# fuzzy_match_table = "customer_data_10_email_deduped_run_2_output"
# refined_database_name = "fluent_dev_filu_db_refined_dev"
demographic_table = "fig_t_demographic"
baseid_table = "fig_t_baseid"


# Configuration Variables - Crawler Catalog
fuzzy_match_database = None
fuzzy_match_table = None
refined_database_name = None
# Clear files in Output bucket
output_bucket = None
output_path = None
file_filter = "run"

first_source = None
glue_role = None

date = datetime.datetime.utcnow().date()
args = getResolvedOptions(sys.argv,
                          ['JOB_NAME',
                          'fuzzy_match_database',
                          'fuzzy_match_table',
                          'refined_database'
                          'output_bucket',
                          'output_path',
                          'GLUE_ROLE',
                          'first_source'])
job.init(args['JOB_NAME'], args)

if ('fuzzy_match_database' not in args or 'fuzzy_match_table' not in args or 'output_bucket' 
    not in args or 'output_path' not in args or 'refined_database' not in args
    or 'first_source' not in args or 'GLUE_ROLE' not in args 
    or args['fuzzy_match_database'] is None or args['fuzzy_match_table'] is None
    or args['refined_database'] is None or args['output_bucket'] is None 
    or args['output_path'] is None or args['first_source'] is None or args['GLUE_ROLE'] is None
    or args['fuzzy_match_database'] == '' or args['fuzzy_match_table'] == '' or args['refined_database'] == ''
    or args['output_bucket'] == '' or args['output_path'] == '' 
    or args['first_source'] == '' or args['GLUE_ROLE'] == ''): 
    #write out an error message and exit
    logger.error('An input parameter was not passed in correctly')
    missingInput = ''
    if args['fuzzy_match_database'] is None:
        missingInput = 'fuzzy_match_database'
    if args['fuzzy_match_table'] is None: 
        missingInput = 'fuzzy_match_table'
    if args['output_bucket'] is None:
        missingInput = 'output_bucket'
    if args['output_path'] is None:
        missingInput = 'output_path'
    if args['first_source'] is None:
        missingInput = 'first_source'
    if args['GLUE_ROLE'] is None:
        missingInput = 'GLUE_ROLE'
    if args['refined_database'] is None:
        missingInput =  'refined_database'
    logger.error('** The input Variable ' + missingInput + ' is not present in the input for Job: ' + args['JOB_NAME'])
    sys.exit(1)
else: 
    fuzzy_match_database = args['fuzzy_match_database']
    fuzzy_match_table = args['fuzzy_match_table']
    output_bucket = args['output_bucket']   
    output_path = args['output_path']
    first_source = args['first_source']
    glue_role = args['GLUE_ROLE']
    refined_database_name = args['refined_database']

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

def write_view_table_to_s3(df,table_name):
    df_audit = create_audit_columns(df)
    dyf = DynamicFrame.fromDF(df_audit,glueContext,table_name)
    output_dir = "s3://" + output_bucket + "/" + output_path + "/" + table_name.lower() + "/"
    partition_keys = ["create_year","create_month","create_date"]
    connectionOptions = {"path": output_dir,"partitionKeys": partition_keys}
    glueContext.write_dynamic_frame_from_options(frame=dyf, \
                                                connection_type = "s3", \
                                                connection_options = connectionOptions, \
                                                format="parquet")
    return "Table: '" + table_name + "' written to '"+ output_dir + "' successfully"                                           

s3 = boto3.resource('s3')
bucket = s3.Bucket(output_bucket)

for obj in bucket.objects.filter(Prefix=output_path + "/" + file_filter):
    s3.Object(bucket.name, obj.key).delete()

## Change Year, Month Range, Date Range Here
create_year=2020
start_month=1
end_month=12
start_date=1
end_date=31
## Ex: partition_predicate = """create_year=2020 AND create_month=05 AND create_date=12"""
partition_predicate = """create_year={} AND
                        create_month BETWEEN {} AND {} AND
                        create_date BETWEEN {} AND {}""".format(create_year,start_month,end_month,start_date,end_date)
logger.info("Partiton Predicate" + partition_predicate)

##Demographic Table
fig_demographic_dyf =  glueContext.create_dynamic_frame_from_catalog(database=refined_database_name,table_name=demographic_table,format="parquet",push_down_predicate=partition_predicate)
fig_demographic_dyf.printSchema()

##BaseID Table
baseid_dyf =  glueContext.create_dynamic_frame.from_catalog(database=refined_database_name,table_name=baseid_table,push_down_predicate=partition_predicate)
baseid_dyf.printSchema()

##FuzzyMatch Table
fuzzymatch_dyf =  glueContext.create_dynamic_frame_from_catalog(database=fuzzy_match_database, table_name=fuzzy_match_table, format="csv") 
fuzzymatch_dyf.printSchema()

##CreateTempViewsForDataframes
fig_demographic_dyf.toDF().createOrReplaceTempView("fig_demographic")
baseid_dyf.toDF().createOrReplaceTempView("fig_baseid")
fuzzymatch_dyf.toDF().createOrReplaceTempView("fig_fuzzy_match_dedup")

### Transformations using SQL Scripts

## Customer Email
customer_email_view_table_name = "customer_email"
customer_email_view = spark.sql("""SELECT DISTINCT
                            base64(md5(coalesce(lower(b.email), ''))) AS customer_email_id,
                            b.email
                            FROM fig_fuzzy_match_dedup as fm
                            INNER JOIN fig_baseid as b
                            ON fm.bid = b.bid
                            GROUP BY b.email""")
response =  write_view_table_to_s3(customer_email_view,customer_email_view_table_name)
logger.info(response)          

## Customer Address
customer_address_view_table_name = "customer_address"
customer_address_view = spark.sql("""SELECT DISTINCT
                                        base64(md5(coalesce(lower(d.address1), '') || coalesce(lower(d.address2), '') || 
                                        coalesce(lower(d.city), '') || coalesce(lower(d.state), '') || coalesce(d.zippost, '') || 
                                        coalesce(cast(d.zipplus4 as string), ''))) AS customer_address_id,
                                        d.address1,
                                        d.address2,
                                        d.city,
                                        d.state,
                                        d.zippost,
                                        d.zipplus4
                                        FROM fig_fuzzy_match_dedup as fm
                                        INNER JOIN fig_baseid as b
                                        ON fm.bid = b.bid
                                        INNER JOIN fig_demographic as d
                                        ON b.bid = d.bid
                                        GROUP BY d.address1, d.address2, d.city, d.state, d.zippost, d.zipplus4""")
response =  write_view_table_to_s3(customer_address_view,customer_address_view_table_name)
logger.info(response)

## Customer Name
customer_name_view_table_name = "customer_name"
customer_name_view = spark.sql("""SELECT DISTINCT
                                    base64(md5(coalesce(lower(d.firstname), '') || coalesce(lower(d.lastname), ''))) as customer_name_id,
                                    d.firstname,
                                    d.lastname
                                    FROM fig_fuzzy_match_dedup as fm
                                    INNER JOIN fig_baseid as b
                                    ON fm.bid = b.bid
                                    INNER JOIN fig_demographic as d
                                    ON b.bid = d.bid
                                    GROUP BY d.firstname, d.lastname""")
response =  write_view_table_to_s3(customer_name_view,customer_name_view_table_name)
logger.info(response)
## Customer phone
customer_phone_view_table_name = "customer_phone"
customer_phone_view = spark.sql("""SELECT DISTINCT
                                    base64(md5(coalesce(lower(d.phone), ''))) as customer_phone_id,
                                    d.phone
                                    FROM fig_fuzzy_match_dedup as fm
                                    INNER JOIN fig_baseid as b
                                    ON fm.bid = b.bid
                                    INNER JOIN fig_demographic as d
                                    ON b.bid = d.bid
                                    GROUP BY d.phone""")
response =  write_view_table_to_s3(customer_phone_view,customer_phone_view_table_name)
logger.info(response)

## Fig-X-Customer
customer_x_view_table_name = "fig_baseid_x_customer"
customer_x_view = spark.sql("""SELECT
                                    base64(md5(cast(fm.bid as string))) AS customer_id,
                                    fm.bid
                                    FROM fig_fuzzy_match_dedup as fm
                                    INNER JOIN fig_demographic as d
                                    ON fm.bid = d.bid
                                    GROUP BY fm.bid, fm.match_id""")
response = write_view_table_to_s3(customer_x_view,customer_x_view_table_name)
logger.info(response)
# Customer View
customer_view_table_name = "customer"
customer_view = spark.sql("""
                SELECT customer_id,
                customer_email_id,
                customer_name_id,
                customer_address_id,
                customer_phone_id,
                if(parent_bid IS NULL,NULL,base64(md5(cast(parent_bid as string)))) AS parent_customer_id
                FROM (
                    SELECT
                    base64(md5(cast(fm.bid as string))) AS customer_id,
                    fm.bid,
                    base64(md5(coalesce(lower(d.email), ''))) AS customer_email_id,
                    base64(md5(coalesce(lower(d.firstname), '') || coalesce(lower(d.lastname), ''))) AS customer_name_id,
                    base64(md5(coalesce(lower(d.address1), '') ||
                    coalesce(lower(d.address2), '') || coalesce(lower(d.city), '') ||
                    coalesce(lower(d.state), '') || coalesce(d.zippost, '') ||
                    coalesce(cast(d.zipplus4 as string), ''))) AS customer_address_id,
                    base64(md5(coalesce(lower(d.phone), ''))) as customer_phone_id,
                    nullif(first_value(fm.bid) OVER (PARTITION BY fm.match_id ORDER BY fm.bid), fm.bid) AS parent_bid
                    FROM fig_fuzzy_match_dedup as fm
                    INNER JOIN fig_demographic as d
                    ON fm.bid = d.bid
                    GROUP BY
                    customer_id,fm.bid,customer_email_id,
                    customer_name_id,customer_address_id,customer_phone_id,fm.match_id
                    ) 
                AS cte_customer
                GROUP BY
                customer_id,
                customer_email_id,
                customer_name_id,
                customer_address_id,
                customer_phone_id,
                parent_bid
                """)
response = write_view_table_to_s3(customer_view,customer_view_table_name)
logger.info(response)