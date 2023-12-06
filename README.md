# upload

Uploads specific SoS files to PO.DAAC S3 bucket for ingestion.

## invoke

Command to invoke lambda via the AWS CLI:

```
aws lambda invoke \
   --cli-binary-format raw-in-base64-out \
   --function-name prefix-upload \
   --invocation-type Event \
   --profile named_profile \
   --payload '{"sos_bucket": "prefix-sos", "podaac_bucket": "podaac-bucket-name", "run_type": "constrained", "version": "0001", "file_list": ["af_sword_v15_SOS_priors.nc", "af_sword_v15_SOS_results.nc"]}' \
   prefix-upload.json
```

Notes:

1. `prefix` : Change this to match whatever environment you may be running in, e.g.: "confluence-dev1"
2. `named_profile` : Change this to the name of the profile used to authenticate to AWS services
3. `podaac-bucket-name` : Change this to the name of the PO.DAAC bucket data will be uploaded to
4. `file_list` : Is a list of SoS files that you would like to upload found at the `run_type/version` key in the SoS S3 bucket.

## aws infrastructure

The renew program includes the following AWS services:

- Lambda function to execute code deployed via zip file.
- IAM role and policy for Lambda function execution.

## deployment

There is a script to deploy the Lambda function AWS infrastructure called `deploy.sh`.

REQUIRES:

- AWS CLI (<https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>)
- Terraform (<https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli>)

Command line arguments:

 [1] app_name: Name of application to create a zipped deployment package for
 [2] s3_state_bucket: Name of the S3 bucket to store Terraform state in (no need for s3:// prefix)
 [3] profile: Name of profile used to authenticate AWS CLI commands

# Example usage: `./delpoy-lambda.sh "my-app-name" "s3-state-bucket-name" "confluence-named-profile"`
