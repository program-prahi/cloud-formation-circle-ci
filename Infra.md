# Datalake for Force Therapeutics

This repo will allow you completely create a data lake in S3.  It consists of a series of top level CloudFormation templates. The template `datalake.yaml` at the current level is the parent template to be run in CloudFormation.  The templates under the `./datalake/` path are components to make nested stacks. Those templates are called from the current level `datalake.yaml` templates and never directly.



![](../assets/force-system.png)

## Datalake Infrastructure

Components: 

[Datalake Infrastructure Stack](./datalake.yaml)

  - [KMS Customer Managed Key](./datalake/kms.yaml)
  - [S3 Raw Data Bucket](./datalake/bucket.yaml)
  - [S3 Refined Data Bucket](./datalake/bucket.yaml)
  - [S3 Transient Data Bucket](./datalake/bucket.yaml)
  - [S3 Glue Temporary Bucket](./datalake/bucket.yaml)
  - [S3 Athena Query Bucket](./datalake/bucket.yaml)
  - [Kinesis Data Stream](./datalake/kinesis-datastream.yaml)
  - [Kinesis Delivery Stream](./datalake/kinesis-firehose.yaml)
    - Glue Database
        - Description
    - Glue Table
        - Description
    - Log Group and Log Stream
        - Description
    - Delivery Stream Policy
        - Allows Glue, S3, Lambda, Logs, Kinesis and KMS.
    - Delivery Stream Role
        - Delivery Stream Policy
    - Delivery Stream
  - [Public VPC](./datalake/default-vpc.yaml)
    - Internet Gateway and attach it to VPC
    - Public Subnets (2)
    - Public Route Tables for Public Subnets (2)
    - Security Group for inbound mysql from DB.
  - [DMS Replication Instance](./datalake/dmsreplicationinstance.yaml)
    - Replication Subnet Group
        - Description
    - Replication Instance
        - Description
  - [DMS SNS Topic](./datalake/dms-sns-topic.yaml)
    - SNS Topic
        - Description
    - SNS Topic Policy
        - Description
  - [DB Secret](./datalake/secret.yaml)
  - [DMS Endpoint](./datalake/dms-endpoint.yaml)
    - Source Endpoint
        - Connects to the Source database
    - DMS Kinesis Policy
        - Allows DMS to put records to kinesis data stream
    - DMS Kinesis Role
        - DMS Kinesis Policy
    - DMS Kineis Target Endpoint
        - CDC are pushed to Kinesis data stream
    - DMS S3 Policy
        - Allow DMS to put records at Raw bucket
    - DMS S3 Role
        - DMS S3 Policy
    - DMS S3 Target Endpoint
        - Full Load are pushed to raw bucket
  - [DMS Tasks](./datalake/dms-tasks.yaml)
    - DMS CDC Task
        - Description
    - DMS Full Load Task
        - Description
    - DMS Event Subscription
        - Description
  - [Glue IAM Roles and Policies](./datalake/iam.yaml)
    - Refined Bucket Access Policy
      - Allow read/write/list to Refined bucket
      - Allow KMS encrypt/decrypt
    - Raw Bucket Access Policy
      - Allow read/write/list to Raw bucket
      - Allow KMS encrypt/decrypt
    - Transient Bucket Access Policy
      - Allow read/write/list to Transient bucket
      - Allow KMS encrypt/decrypt
    - Glue Temp Bucket Access Policy
      - Allow read/write/list to Glue Temp bucket
      - Allow KMS encrypt/decrypt
    - Athena Query Bucket Access Policy
      - Allow read/write/list to Athena Query bucket
      - Allow KMS encrypt/decrypt
    - KMS Policy
      - Allow KMS encrypt/decrypt
    - Cloudwatch Logging Policy
      - Allow Writing Logs to Log Bucket
      - Allow KMS encrypt/decrypt
    - Invoke Lambda Policy
      - Allow invoking lambda function for account
    - Refined Bucket Role
      - Refined Bucket Access Policy
    - Raw Bucket Role
      - Raw Bucket Access Policy
    - Glue Repo Bucket Role
      - Glue Repo Bucket Access Policy
    - Glue Temp Bucket Role
      - Glue Temp Bucket Access Policy
    - Glue Refined Data Crawler Role
      - Allow Glue Service Role
      - S3 Refined Data Bucket Policy
    - Glue Raw Data Crawler Role
      - Allow Glue Service Role
      - S3 Raw Data Bucket Policy
    - Glue Etl Job Role
      - Allow Glue Service Role
      - S3 Refined Bucket Policy
      - S3 Raw Bucket Policy
      - S3 Glue Repo Bucket Policy
      - S3 Glue Temp Buvket Policy
      - Cloudwatch Logging Policy
      - Invoke Lambda Policy
      - Allow Delete Object in all Raw Bucket
      - Allow Delete Object in all Refined Bucket
      - Allow Delete Object in all Glue Repo Bucket
      - Allow Delete Object in all Glue Temp Bucket
    - Cloudwatch Event Role
      - Allow Cloudwatch Events Role
      - Cloudwatch Logging Policy
      - Invoke Lambda Policy
  - [Crawler to Scan RAW data tables](./datalake/glue-crawler.yaml)
    - Creates a Glue Database
    - Creates a Glue Crawler
    - Creates a Glue Security Configuration for the crawler to enforce SSE with the KMS Key
  - [Crawler to Scan REFINED data tables](./datalake/glue-crawler.yaml)
    - Creates a Glue Database
    - Creates a Glue Crawler
    - Creates a Glue Security Configuration for the crawler to enforce SSE with the KMS Key


# Deploying to New Environment and Setup

1.	Create new AWS Account
    1. Log into new AWS Account and create a non-root user with AdministratorAccess 
    2. Log in with new user

2.	Clone Git Repo
    1.	<Link>
    2.	Note local location of repo. Ex: /home/user/fluent-data-lake
3. Open the /home/user/parameters.json file
    1. Give required parameters information as specified in the table below:


  |Parameter Name|Description & Utilization|Allowed Values|Default Value|Required?|
  |:---:|:---:|:---:|:---:|:---:|
  |CompanyName|S3 bucket naming conventions for the company the stuff is all for.|<Any String>|fluent|Optional|
  |CodaS3BucketName|S3 bucket where the Quick Start templates and scripts are installed.|<Any String>|fluent-datalake-templates-dev-394780878318|Optional|
  |CodaS3KeyPrefix|S3 key prefix used to simulate a folder for your copy of Quick Start assets.|<Any String>|data-lake/|Optional|
  |ProjectName|Name of the project for tagging purposes.|<Any String>|datalake|Optional|
  |Owner|Name of the Owner of the resources for tagging purposes.|<Any String>|Jacob Puthuparambil|Optional|
  |Environment|On which environment the resources to be created.| dev/ qa/ staging/ production| |Required|
  |VpcCIDR|The IP range (CIDR notation) for this VPC| '((\d{1,3})\.){3}\d{1,3}/\d{1,2}' |10.192.0.0/16|Optional|
  |PublicSubnet1CIDR|The IP range (CIDR notation) for this Public Subnet 1| '((\d{1,3})\.){3}\d{1,3}/\d{1,2}' |10.192.50.0/24|Optional|
  |PublicSubnet2CIDR|The IP range (CIDR notation) for this Public Subnet 2| '((\d{1,3})\.){3}\d{1,3}/\d{1,2}' |10.192.40.0/24|Optional|
  |ReplicationInstanceClass|Instance type of Replication Instance.| dms.t2.micro\ dms.t2.small\ dms.t2.medium\ dms.t2.large\ dms.c4.large\ dms.c4.xlarge\ dms.c4.2xlarge\ dms.c4.4xlarge|dms.c4.2xlarge|Optional|
  |EndpointBucketFolder|Prefix of raw bucket where the full load data populated| |fig_full_load|Optional|
  |Username|Username of the Database| |awsdatalake|Optional|
  |Password|Password of the Database| | |Required|
  |Engine|Engine type of the Database| | mysql |Optional|
  |Host|Host address of the Database| | 34.74.194.212 |Optional|
  |Port|Port of the Database| | 3306 |Optional|
  |DBName|Name of the Database| | FILU |Optional|
  |RawInputDatabaseName|Name of the Raw Zone Database| |fluent_dev_filu_db_raw|Optional|
  |TransientInputDatabaseName|Name of the Transient Zone Database| |fluent_dev_filu_db_transient|Optional|
  |RefinedInputDatabaseName|Name of the Refined Zone Database| |fluent_dev_filu_db_refined|Optional|
  |EmailID|Email ID for sns to notify the glue workflow failure.| | |Required|

      Note:
        * “Optional” parameter indicates that if the parameter value is not passed then the default value will be used.
4.  Create a S3 Bucket to store the CloudFormation templates. 
      Note:
        * S3 bucket should be in the same region where the Cloudformation stacks wants to be deployed. 
5.	Create a secret that stores the details of the Source Database. The secret should contain:

  |Key|Value|
  |:---:|:---:|
  |Username|awsdatalake|
  |Password||
  |Host|34.74.194.212|
  |DBName|FILU|

6.  Create a new user with programmatic access for deploying the stacks using CircleCI. Note the Key values to store them as environment variables.
7.  Open the CircleCI dashboard and Link the `fluent-datalake` project.  
8.  Goto the Project Settings> Environment Variables, Add the following Environment Varibles to the project

  |Key|Description|
  |:---:|:---:|
  |AWS_ACCESS_KEY_ID|Access Key value of the user you have created before.|
  |AWS_SECRET_ACCESS_KEY|Secret Key value of the user you have created before.|
  |AWS_DEFAULT_REGION|Region where the stacks to be deployed.|
  |AWS_SECRET_NAME|Name of the AWS Secret that has the details of Database|
  |AWS_SECRET_REGION|Region of the AWS Secret that has the details of Database|
  |STACK_NAME|Name of the Cloudformation Stack|
  |SYNC_BUCKET_NAME|Name of the bucket where the Cloudformation templates to be stored|

9.  For every push to the `master` branch, CircleCI will create/update the stack.