# S3 Bucket outputs
output "books_bucket_name" {
  description = "Name of the S3 bucket for books"
  value       = aws_s3_bucket.books.id
}

output "books_bucket_arn" {
  description = "ARN of the S3 bucket for books"
  value       = aws_s3_bucket.books.arn
}

output "frontend_bucket_name" {
  description = "Name of the S3 bucket for frontend"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_website_endpoint" {
  description = "Website endpoint for frontend bucket"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "frontend_bucket_website_url" {
  description = "Full URL for frontend website"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

# DynamoDB outputs
output "books_table_name" {
  description = "Name of the Books DynamoDB table"
  value       = aws_dynamodb_table.books.name
}

output "books_table_arn" {
  description = "ARN of the Books DynamoDB table"
  value       = aws_dynamodb_table.books.arn
}

output "user_books_table_name" {
  description = "Name of the User Books DynamoDB table"
  value       = aws_dynamodb_table.user_books.name
}

output "user_books_table_arn" {
  description = "ARN of the User Books DynamoDB table"
  value       = aws_dynamodb_table.user_books.arn
}

output "authors_table_name" {
  description = "Name of the Authors DynamoDB table"
  value       = aws_dynamodb_table.authors.name
}

output "authors_table_arn" {
  description = "ARN of the Authors DynamoDB table"
  value       = aws_dynamodb_table.authors.arn
}

# Cognito outputs
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.main.id
}

output "cognito_domain" {
  description = "Cognito User Pool domain (if configured)"
  value       = var.cognito_domain_prefix != "" ? aws_cognito_user_pool_domain.main[0].domain : ""
}

# IAM outputs
output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_execution_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.name
}

# Configuration helper outputs
output "samconfig_parameters" {
  description = "Parameters to use in samconfig.toml"
  value = {
    BucketName          = aws_s3_bucket.books.id
    CognitoUserPoolId   = aws_cognito_user_pool.main.id
    CognitoUserPoolArn  = aws_cognito_user_pool.main.arn
    CognitoClientId     = aws_cognito_user_pool_client.main.id
  }
}

output "frontend_config" {
  description = "Configuration values for frontend/config.js"
  value = {
    userPoolId = aws_cognito_user_pool.main.id
    clientId   = aws_cognito_user_pool_client.main.id
    region     = var.aws_region
  }
}

# Summary output
output "setup_complete" {
  description = "Summary of created resources"
  value = <<-EOT
    ====================================
    Books Library Infrastructure Setup
    ====================================
    
    S3 Buckets:
      - Books: ${aws_s3_bucket.books.id}
      - Frontend: ${aws_s3_bucket.frontend.id}
      - Frontend URL: http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}
    
    DynamoDB Tables:
      - Books: ${aws_dynamodb_table.books.name}
      - User Books: ${aws_dynamodb_table.user_books.name}
      - Authors: ${aws_dynamodb_table.authors.name}
    
    Cognito:
      - User Pool ID: ${aws_cognito_user_pool.main.id}
      - Client ID: ${aws_cognito_user_pool_client.main.id}
      - Region: ${var.aws_region}
    
    Next Steps:
    1. Update samconfig.toml with the values above
    2. Run 'sam build && sam deploy'
    3. Update frontend/config.js with Cognito values
    4. Deploy frontend: aws s3 sync frontend/ s3://${aws_s3_bucket.frontend.id}/
    5. Configure S3 trigger: ./scripts/configure-s3-trigger.sh
  EOT
}
