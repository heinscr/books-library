terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  # Optional: use a specific profile
  # profile = var.aws_profile
}

# S3 Bucket for Books (covers)
resource "aws_s3_bucket" "books" {
  bucket = var.books_bucket_name
  
  tags = {
    Name        = "Books Library - Books Bucket"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Enable versioning for books bucket
resource "aws_s3_bucket_versioning" "books" {
  bucket = aws_s3_bucket.books.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access for books bucket
resource "aws_s3_bucket_public_access_block" "books" {
  bucket = aws_s3_bucket.books.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for books bucket
resource "aws_s3_bucket_cors_configuration" "books" {
  bucket = aws_s3_bucket.books.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# S3 Bucket for Frontend hosting
resource "aws_s3_bucket" "frontend" {
  bucket = var.frontend_bucket_name
  
  tags = {
    Name        = "Books Library - Frontend"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Enable versioning for frontend bucket
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Configure frontend bucket for static website hosting
resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# Public access configuration for frontend (if hosting publicly)
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Bucket policy for frontend (public read access)
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
  
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# DynamoDB Table for Books
resource "aws_dynamodb_table" "books" {
  name           = var.books_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "author"
    type = "S"
  }

  attribute {
    name = "title"
    type = "S"
  }

  # GSI for querying by author
  global_secondary_index {
    name            = "AuthorIndex"
    hash_key        = "author"
    range_key       = "title"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  tags = {
    Name        = "Books Library - Books Table"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# DynamoDB Table for User Books (read status)
resource "aws_dynamodb_table" "user_books" {
  name           = var.user_books_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "userId"
  range_key      = "bookId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "bookId"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  tags = {
    Name        = "Books Library - User Books Table"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# DynamoDB Table for Authors
resource "aws_dynamodb_table" "authors" {
  name           = var.authors_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "name"

  attribute {
    name = "name"
    type = "S"
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  tags = {
    Name        = "Books Library - Authors Table"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = var.cognito_user_pool_name

  # Password policy
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # Email configuration
  auto_verified_attributes = ["email"]
  
  username_attributes = ["email"]

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # User attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Custom attribute for admin status
  schema {
    name                = "isAdmin"
    attribute_data_type = "String"
    mutable             = true
    
    string_attribute_constraints {
      min_length = 1
      max_length = 10
    }
  }

  tags = {
    Name        = "Books Library - User Pool"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.cognito_user_pool_name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # OAuth settings
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  
  callback_urls = var.cognito_callback_urls
  logout_urls   = var.cognito_logout_urls

  # Supported identity providers
  supported_identity_providers = ["COGNITO"]

  # Token validity
  id_token_validity     = 60  # minutes
  access_token_validity = 60  # minutes
  refresh_token_validity = 30 # days

  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "days"
  }

  # Security
  prevent_user_existence_errors = "ENABLED"
  
  # Allow authentication flow
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  count        = var.cognito_domain_prefix != "" ? 1 : 0
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}

# IAM Role for Lambda execution (referenced by SAM)
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "Books Library - Lambda Execution Role"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM Policy for Lambda to access DynamoDB
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${var.project_name}-lambda-dynamodb-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.books.arn,
          "${aws_dynamodb_table.books.arn}/index/*",
          aws_dynamodb_table.user_books.arn,
          aws_dynamodb_table.authors.arn
        ]
      }
    ]
  })
}

# IAM Policy for Lambda to access S3
resource "aws_iam_role_policy" "lambda_s3" {
  name = "${var.project_name}-lambda-s3-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.books.arn,
          "${aws_s3_bucket.books.arn}/*"
        ]
      }
    ]
  })
}
