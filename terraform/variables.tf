variable "app_name" {
  type        = string
  description = "Application name"
  default     = "confluence"
}

variable "app_version" {
  type        = number
  description = "The application version number"
  default     = 0.1
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

variable "environment" {
  type        = string
  description = "The environment in which to deploy to"
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
  description = "CNM SNS Topic ARN to publish to"
}

variable "prefix" {
  type        = string
  description = "Prefix to add to all AWS resources as a unique identifier"
}
