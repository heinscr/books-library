variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "aws_profile" {
  description = "AWS CLI profile to use (optional)"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "books-library"
}

# S3 Buckets
variable "books_bucket_name" {
  description = "Name for the S3 bucket storing book covers"
  type        = string
}

variable "frontend_bucket_name" {
  description = "Name for the S3 bucket hosting the frontend"
  type        = string
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

# DynamoDB Tables
variable "books_table_name" {
  description = "Name for the Books DynamoDB table"
  type        = string
  default     = "Books"
}

variable "user_books_table_name" {
  description = "Name for the User Books DynamoDB table"
  type        = string
  default     = "UserBooks"
}

variable "authors_table_name" {
  description = "Name for the Authors DynamoDB table"
  type        = string
  default     = "Authors"
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery for DynamoDB tables"
  type        = bool
  default     = false
}

# Cognito
variable "cognito_user_pool_name" {
  description = "Name for the Cognito User Pool"
  type        = string
  default     = "books-library-users"
}

variable "cognito_callback_urls" {
  description = "List of callback URLs for Cognito"
  type        = list(string)
  default     = ["http://localhost:8000"]
}

variable "cognito_logout_urls" {
  description = "List of logout URLs for Cognito"
  type        = list(string)
  default     = ["http://localhost:8000"]
}

variable "cognito_domain_prefix" {
  description = "Domain prefix for Cognito hosted UI (leave empty to skip)"
  type        = string
  default     = ""
}
