"""AWS Lambda that uploads SoS to PO.DAAC and triggers ingestion.

Retrieves S3 credentials from the SSM parameter store and uploads all files 
specified by a prefix (or directory) found in the confluence-sos S3 Bucket.

Publishes CNM message to SNS Topic to kick off ingestion of SoS granules.
"""

# Standard imports
import datetime
import hashlib
import json
import os
import pathlib
import sys

# Third-party imports
import boto3
import botocore
from netCDF4 import Dataset

# Constants
TMP_STORAGE = pathlib.Path("/tmp")
PROVIDER = "NASA/JPL/PO.DAAC"
COLLECTION = "SWOT_L4_DAWG_SOS_DISCHARGE"
VERSION = "1.4"

def handler(event, context):
    
    start = datetime.datetime.now()
    
    sos_bucket = "None" if "sos_bucket" not in event.keys() else event["sos_bucket"]
    podaac_bucket = event["podaac_bucket"]
    run_type = "None" if "run_type" not in event.keys() else event["run_type"]
    version = event["version"]
    file_list = event["file_list"]
    publish_only = "false" if "publish_only" not in event.keys() else event["publish_only"]
    publish = "false" if "publish" not in event.keys() else event["publish"]
    
    try:
        if publish_only == "true":
            publish_cnm_message(podaac_bucket, version, file_list, publish_only=publish_only)     
        else:        
            upload_and_publish(sos_bucket, podaac_bucket, run_type, version, file_list, publish)
    except botocore.exceptions.ClientError as e:
        print("Error encountered.")
        print(e)
        sys.exit(1)
        
    end = datetime.datetime.now()
    print(f"Execution time: {end - start}")
        
def publish_cnm_message(podaac_bucket, version, file_list, download_list=[], publish_only="false"):
    """Publish CNM message to kick off ingestion of SoS granules."""
    
    publish_dict = group_sos_files(file_list)
    if publish_only == "true":
        creds = get_podaac_creds()
        print("Retrieved PO.DAAC S3 credentials.")
        
        download_list = download_podaac(podaac_bucket, file_list, creds)
        print("Downloaded SoS from PO.DAAC.")
        for download in download_list: print(f"Downloaded SoS file: {download}.")
        
    retrieve_size_checksum(publish_dict, download_list)
    
    for granule in publish_dict.values():
        message = create_message(podaac_bucket, version, granule)
        print(f"Message created: {message}")
        publish_message(message)
        
    if publish_only == "true":
        clear_tmp(download_list)
        
def group_sos_files(sos_list):
    """Organize list of SoS files into a dictionary of continent keys."""
    
    continents = [ sos.split('_')[0] for sos in sos_list ]
    continents = list(set(continents))
    
    upload_dict = {}
    for continent in continents:
        upload_dict[continent] = {}
        for sos in sos_list:
            if continent in sos:                    
                    if "priors" in sos:
                        upload_dict[continent]["priors"] = sos
                    
                    if "results" in sos:
                        upload_dict[continent]["results"] = sos
    
    return upload_dict

def download_podaac(podaac_bucket, file_list, creds):
    """Download files from PO.DAAC S3 Bucket to temporary local storage."""
    
    s3 = boto3.client("s3",
                      aws_access_key_id=creds["access_key"],
                      aws_secret_access_key=creds["secret"])
    download_list = []
    try:
        for file_name in file_list:
            print(podaac_bucket, f"{COLLECTION}/{file_name}")
            tmp_file = TMP_STORAGE.joinpath(file_name)
            s3.download_file(podaac_bucket,
                             f"{COLLECTION}/{file_name}",
                             tmp_file)
            download_list.append(file_name)
    except botocore.exceptions.ClientError as e:
        raise e
    return download_list

def retrieve_size_checksum(publish_dict, download_list):
    """Update publish_dict with checksum and file size for files in dictionary."""
    
    for download in download_list:
        continent = download.split('_')[0]
        if "priors" in download:
            publish_dict[continent]["priors"] = { "file": publish_dict[continent]["priors"] }
            publish_dict[continent]["priors"]["checksum"] = get_checksum(TMP_STORAGE.joinpath(download))
            publish_dict[continent]["priors"]["size"] = os.stat(TMP_STORAGE.joinpath(download)).st_size
        if "results" in download:
            publish_dict[continent]["results"] = { "file": publish_dict[continent]["results"] }
            publish_dict[continent]["results"]["checksum"] = get_checksum(TMP_STORAGE.joinpath(download))
            publish_dict[continent]["results"]["size"] = os.stat(TMP_STORAGE.joinpath(download)).st_size
        
def create_message(podaac_bucket, version, granule):
        """Create message to be published."""
        
        priors_file = granule["priors"]["file"]
        results_file = granule["results"]["file"]
        identifier = f"{priors_file.split('_priors')[0]}"  
        message = {
            "version": VERSION,
            "provider": PROVIDER,
            "collection": COLLECTION,
            "submissionTime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "identifier": identifier,
            "product": {
                "name": identifier,
                "files": [
                    {
                        "uri": f"s3://{podaac_bucket}/{COLLECTION}/{results_file}",
                        "checksum": granule["results"]["checksum"],
                        "size": granule["results"]["size"],
                        "type": "data",
                        "name": results_file,
                        "checksumType": "md5"
                    },
                    {
                        "uri": f"s3://{podaac_bucket}/{COLLECTION}/{priors_file}",
                        "checksum": granule["priors"]["checksum"],
                        "size": granule["priors"]["size"],
                        "type": "data",
                        "name": priors_file,
                        "checksumType": "md5"
                    }
                ],
                "dataVersion": str(int(version))
            }
        }
        
        return message
        
def get_checksum(file_path):
    """Return checksum for file contents."""
    
    with open(file_path, "rb") as f:
        bytes = f.read()
        checksum = hashlib.md5(bytes).hexdigest()
    return checksum

def publish_message(message):
    """Publish CNM message to SNS Topic."""
    
    topic_arn = get_cross_account()
    sns = boto3.client("sns", region_name="us-west-2")
    try:
        response = sns.publish(
            TopicArn = topic_arn,
            Message = json.dumps(message),
        )
        print(f"{message['identifier']} message published to SNS Topic: {topic_arn}")
    except botocore.exceptions.ClientError as e:
        raise e
    
def get_cross_account():
    """Return PO.DAAC CNM cross account info."""
    
    ssm_client = boto3.client('ssm', region_name="us-west-2")
    try:
        topic_arn = ssm_client.get_parameter(Name="podaac_cnm_topic_arn", WithDecryption=True)["Parameter"]["Value"]
    except botocore.exceptions.ClientError as e:
        raise e
    return topic_arn
        
def upload_and_publish(sos_bucket, podaac_bucket, run_type, version, file_list, publish):
    """Upload the SoS to S3 bucket and publish CNM message for ingestion."""
    
    # Download SoS files
    download_list = download_sos(sos_bucket, run_type, version, file_list)
    print(f"Downloaded SoS files from {sos_bucket}.")
    for download in download_list: print(f"Downloaded SoS file: {download}.")
    
    # Get and store PODAAC credentials 
    creds = get_podaac_creds()
    print("Retrieved PO.DAAC S3 credentials.")
    
    # Upload SoS files
    upload_list = upload_sos(podaac_bucket, run_type, version, download_list, creds)
    print(f"Uploaded SoS files to {podaac_bucket}.")
    for upload in upload_list: print(f"Uploaded SoS file: {upload}.")
    
    # Publish CNM
    if publish == "true":
        publish_cnm_message(podaac_bucket, version, upload_list, download_list=download_list)
    
    # Remove SoS files
    clear_tmp(download_list)
    print("Cleared temporary storage.")

def download_sos(sos_bucket, run_type, version, file_list):
    """Download files from SoS S3 Bucket to temporary local storage."""
    
    s3 = boto3.client("s3")    
    download_list = []
    try:
        for file_name in file_list:
            tmp_file = TMP_STORAGE.joinpath(file_name)
            s3.download_file(sos_bucket,
                             f"{run_type}/{version}/{file_name}",
                             tmp_file)
            download_list.append(file_name)
    except botocore.exceptions.ClientError as e:
        raise e
    return download_list

def get_podaac_creds():
    """Return PO.DAAC S3 credentials stored in SSM Parameter Store."""
    
    creds = {}
    ssm_client = boto3.client('ssm', region_name="us-west-2")
    try:
        creds["access_key"] = ssm_client.get_parameter(Name="podaac_key", WithDecryption=True)["Parameter"]["Value"]
        creds["secret"] = ssm_client.get_parameter(Name="podaac_secret", WithDecryption=True)["Parameter"]["Value"]
    except botocore.exceptions.ClientError as e:
        raise e
    return creds

def upload_sos(podaac_bucket, run_type, version, download_list, creds):
    """Upload files to PO.DAAC S3 Bucket from temporary storage."""
    
    s3 = boto3.client("s3",
                      aws_access_key_id=creds["access_key"],
                      aws_secret_access_key=creds["secret"])
          
    upload_dict = group_sos_files(download_list)
    upload_list = []    
    for granule in upload_dict.values():
        priors = TMP_STORAGE.joinpath(granule["priors"])
        results = TMP_STORAGE.joinpath(granule["results"])
        runtime = get_runtime(priors)
        
        try:
            full_priors = f"{priors.name.split('_priors.nc')[0]}_{run_type}_{version}_{runtime}_priors.nc"
            s3.upload_file(str(priors),
                            podaac_bucket,
                            f"{COLLECTION}/{full_priors}")
            upload_list.append(full_priors)
            
            full_result = f"{results.name.split('_results.nc')[0]}_{run_type}_{version}_{runtime}_results.nc"
            s3.upload_file(str(results),
                            podaac_bucket,
                            f"{COLLECTION}/{full_result}")
            upload_list.append(full_result)
        except botocore.exceptions.ClientError as e:
            raise e
    
    return upload_list
    
def get_runtime(file_name):
    """Get runtime timestamp from global attributes of SoS file."""
    
    sos_ds = Dataset(file_name, 'r')
    if "priors" in file_name.name:
        runtime = sos_ds.date_modified
    else:
        runtime = sos_ds.date_created
    sos_ds.close()
    
    runtime_ds = datetime.datetime.strptime(runtime, '%Y-%m-%dT%H:%M:%S').strftime('%Y%m%dT%H%M%S')
    return runtime_ds

def clear_tmp(download_list):
    """Remove downloaded fiels from temporary storage."""
    
    for download in download_list:
        TMP_STORAGE.joinpath(download).unlink()
