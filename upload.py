"""AWS Lambda that uploads SoS to PO.DAAC.

Retrieves S3 credentials from the SSM parameter store and uploads all files 
specified by a prefix (or directory) found in the confluence-sos S3 Bucket.
"""

# Standard imports
import datetime
import pathlib
import sys

# Third-party imports
import boto3
import botocore
from netCDF4 import Dataset

# Constants
TMP_STORAGE = pathlib.Path("/tmp")
PODAAC_KEY = "podaac_key"
PODAAC_SECRET = "podaac_secret"

def handler(event, context):
    
    sos_bucket = event["sos_bucket"]
    podaac_bucket = event["podaac_bucket"]
    run_type = event["run_type"]
    version = event["version"]
    file_list = event["file_list"]
    
    try:
               
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
        
        # Remove SoS files
        clear_tmp(download_list)
        print("Cleared temporary storage.")
    
    except botocore.exceptions.ClientError as e:
        print("Error encountered.")
        print(e)
        sys.exit(1)
    
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
            download_list.append(tmp_file)
    except botocore.exceptions.ClientError as e:
        raise e
    return download_list

def upload_sos(podaac_bucket, run_type, version, download_list, creds):
    """Upload files to PO.DAAC S3 Bucket from temporary storage."""
    
    s3 = boto3.client("s3",
                      aws_access_key_id=creds["access_key"],
                      aws_secret_access_key=creds["secret"])
    upload_list = []
    try:
        for file_name in download_list:
            runtime = get_runtime(file_name)
            full_name = f"{file_name.name.split('.nc')[0]}_{run_type}_{version}_{runtime}.nc"
            s3.upload_file(str(file_name),
                           podaac_bucket,
                           full_name)
            upload_list.append(full_name)
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
        download.unlink()
