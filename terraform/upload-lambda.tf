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

resource "aws_lambda_function_event_invoke_config" "upload_invoke_config" {
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
        "Sid" : "AllGetObjects",
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
        "Sid" : "AllowPublishToTopic",
        "Effect" : "Allow",
        "Action" : [
          "sns:Publish"
        ],
        "Resource" : var.podaac_cnm_topic_arn
      }
    ]
  })
}

# SSM Parameter Store
resource "aws_ssm_parameter" "aws_ssm_parameter_podaac_key" {
  name   = "podaac_key"
  type   = "SecureString"
  value  = var.podaac_key
}

resource "aws_ssm_parameter" "aws_ssm_parameter_podaac_secret" {
  name   = "podaac_secret"
  type   = "SecureString"
  value  = var.podaac_secret
}

resource "aws_ssm_parameter" "aws_ssm_parameter_podaac_cumulus" {
  name   = "podaac_cnm_topic_arn"
  type   = "SecureString"
  value  = var.podaac_cnm_topic_arn
}
