#!/bin/bash
#
# Script to create a zipped deployment package for a Lambda function and deploy
# AWS infrastructure.
#
# Command line arguments:
# [1] app_name: Name of application to create a zipped deployment package for
# [2] s3_state_bucket: Name of the S3 bucket to store Terraform state in (no need for s3:// prefix)
# [3] profile: Name of profile used to authenticate AWS CLI commands
# 
# Example usage: ./delpoy-lambda.sh "my-app-name" "s3-state-bucket-name" "confluence-named-profile" 

APP_NAME=$1
S3_STATE=$2
ROOT_PATH="$PWD"

# Create Zipped Package
deploy/deploy-zip.sh $APP_NAME

# Deploy Terraform
cd terraform
terraform init -reconfigure -backend-config="bucket=$S3_STATE" -backend-config="key=$APP_NAME.tfstate" -backend-config="region=us-west-2"
terraform apply -auto-approve
cd ..