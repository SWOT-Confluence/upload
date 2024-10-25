variable "app_name" {
  type        = string
  description = "Application name"
  default     = "confluence"
}

variable "app_version" {
  type        = number
  description = "The application version number"
}

variable "aws_region" {
  type        = string
  description = "AWS region to deploy to"
  default     = "us-west-2"
}

variable "default_tags" {
  type    = map(string)
  default = {}
}

variable "iam_user" {
  type        = string
  description = "User to allow KMS key for SSM parameter store"
}

variable "podaac_key" {
  type        = string
  default     = "None"
  description = "AWS access key that allows uploading of SoS for ingestion"
}

variable "podaac_secret" {
  type        = string
  default     = "None"
  description = "AWS secret key that allows uploading of SoS for ingestion"
}

variable "podaac_cnm_topic_arn" {
  type        = string
  default     = "None"
  description = "CNM SNS Topic ARN to publish to"
}

variable "podaac_cnm_topic_arns" {
  type        = list(string)
  default     = ["None"]
  description = "List of CNM SNS Topic ARN to allow publication"
}

variable "prefix" {
  type        = string
  description = "Prefix to add to all AWS resources as a unique identifier"
}

variable "profile" {
  type        = string
  description = "Named profile to build infrastructure with"
}