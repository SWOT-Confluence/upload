# AWS Lambda function
resource "aws_lambda_function" "aws_lambda_upload" {
  filename         = "upload.zip"
  function_name    = "${var.prefix}-upload"
  role             = aws_iam_role.aws_lambda_upload_execution_role.arn
  handler          = "upload.handler"
  runtime          = "python3.12"
  source_code_hash = filebase64sha256("upload.zip")
  timeout          = 300
  memory_size      = 2048
  ephemeral_storage {
    size = 10240
  }
    tags = {
    "Name" = "${var.prefix}-upload"
  }
}

resource "aws_lambda_function_event_invoke_config" "example" {
  function_name                = aws_lambda_function.aws_lambda_upload.function_name
  maximum_event_age_in_seconds = 60
  maximum_retry_attempts       = 0
}

# AWS Lambda execution role & policy
resource "aws_iam_role" "aws_lambda_upload_execution_role" {
  name = "${var.prefix}-lambda-upload-execution-role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

# Parameter Store policy
resource "aws_iam_role_policy_attachment" "aws_lambda_get_put_parameter_policy_attach" {
  role       = aws_iam_role.aws_lambda_upload_execution_role.name
  policy_arn = aws_iam_policy.aws_lambda_upload_execution_policy.arn
}

resource "aws_iam_policy" "aws_lambda_upload_execution_policy" {
  name        = "${var.prefix}-lambda-upload-execution-policy"
  description = "Download files from bucket and access Parameter Store."
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "AllowCreatePutLogs",
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "arn:aws:logs:*:*:*"
      },
      {
        "Sid" : "AllowListBuckets",
        "Effect" : "Allow",
        "Action" : [
          "s3:ListBucket",
          "s3:ListBucketVersions"
        ],
        "Resource" : [
          "${data.aws_s3_bucket.s3_sos.arn}"
        ]
      },
      {
        "Sid" : "AllGetPuObjects",
        "Effect" : "Allow",
        "Action" : [
          "s3:GetObject",
        ],
        "Resource" : [
          "${data.aws_s3_bucket.s3_sos.arn}/*"
        ]
      },
      {
        "Sid" : "GetSSMParameter",
        "Effect" : "Allow",
        "Action" : [
          "ssm:GetParameter*"
        ],
        "Resource" : "arn:aws:ssm:us-west-2:${local.account_id}:parameter/podaac_*"
      },
      {
        "Sid" : "DescribeSSMParameter",
        "Effect" : "Allow",
        "Action" : "ssm:DescribeParameters",
        "Resource" : "*"
      },
      {
        "Sid" : "DecryptKey",
        "Effect" : "Allow",
        "Action" : [
          "kms:DescribeKey",
          "kms:Decrypt"
        ],
        "Resource" : "${aws_kms_key.kms_key_ssm.arn}"
      },
      {
        "Sid" : "AllowPublishToTopic",
        "Effect" : "Allow",
        "Action" : [
          "sns:Publish"
        ],
        "Resource" : var.podaac_cnm_topic_arns
      }
    ]
  })
}

# SSM Parameter Store
resource "aws_ssm_parameter" "aws_ssm_parameter_podaac_key" {
  name   = "podaac_key"
  type   = "SecureString"
  key_id = aws_kms_key.kms_key_ssm.id
  value  = var.podaac_key
}

resource "aws_ssm_parameter" "aws_ssm_parameter_podaac_secret" {
  name   = "podaac_secret"
  type   = "SecureString"
  key_id = aws_kms_key.kms_key_ssm.id
  value  = var.podaac_secret
}

resource "aws_ssm_parameter" "aws_ssm_parameter_podaac_cumulus" {
  name   = "podaac_cnm_topic_arn"
  type   = "SecureString"
  key_id = aws_kms_key.kms_key_ssm.id
  value  = var.podaac_cnm_topic_arn
}

# KMS Key
resource "aws_kms_key" "kms_key_ssm" {
  description              = "KMS key for SSM parameter encryption"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  key_usage                = "ENCRYPT_DECRYPT"
  policy = jsonencode({
    "Id" : "key-consolepolicy-3",
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "Enable IAM User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${local.account_id}:root"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      },
      {
        "Sid" : "Allow access for Key Administrators",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${local.account_id}:user/${var.iam_user}"
        },
        "Action" : [
          "kms:Create*",
          "kms:Describe*",
          "kms:Enable*",
          "kms:List*",
          "kms:Put*",
          "kms:Update*",
          "kms:Revoke*",
          "kms:Disable*",
          "kms:Get*",
          "kms:Delete*",
          "kms:TagResource",
          "kms:UntagResource",
          "kms:ScheduleKeyDeletion",
          "kms:CancelKeyDeletion"
        ],
        "Resource" : "*"
      },
      {
        "Sid" : "Allow use of the key",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${local.account_id}:user/${var.iam_user}"
        },
        "Action" : [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        "Resource" : "*"
      },
      {
        "Sid" : "Allow attachment of persistent resources",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${local.account_id}:user/${var.iam_user}"
        },
        "Action" : [
          "kms:CreateGrant",
          "kms:ListGrants",
          "kms:RevokeGrant"
        ],
        "Resource" : "*",
        "Condition" : {
          "Bool" : {
            "kms:GrantIsForAWSResource" : "true"
          }
        }
      }
    ]
  })
}
resource "aws_kms_alias" "kms_alias_ssm" {
  name          = "alias/${var.prefix}-ssm-parameter-store"
  target_key_id = aws_kms_key.kms_key_ssm.key_id
}