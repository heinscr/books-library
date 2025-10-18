#!/bin/bash
# S3 Trigger Configuration Script
# This script configures S3 to trigger the Lambda function when books are uploaded
#
# Environment Variables (optional):
#   AWS_PROFILE: AWS profile name (default: 'default')
#   AWS_REGION: AWS region (default: 'us-east-2')
#   S3_BUCKET: S3 bucket name (default: 'crackpow')
#
# Example usage:
#   # Use defaults
#   ./configure-s3-trigger.sh
#
#   # Use custom profile
#   AWS_PROFILE=my-profile ./configure-s3-trigger.sh
#
#   # Override all settings
#   AWS_PROFILE=prod AWS_REGION=us-west-2 S3_BUCKET=my-books ./configure-s3-trigger.sh

set -e

# Configuration - Update these values for your environment
PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-2}"
BUCKET="${S3_BUCKET:-crackpow}"
FUNCTION_NAME="" # Will be filled after deployment

echo "=== S3 Lambda Trigger Configuration ==="
echo "Using AWS Profile: $PROFILE"
echo "Using AWS Region: $REGION"
echo "Using S3 Bucket: $BUCKET"
echo ""
echo "Step 1: Get the Lambda function ARN from SAM deployment"
echo "After running 'sam deploy', look for the S3TriggerFunction ARN in outputs"
echo ""
read -p "Enter the S3TriggerFunction ARN: " FUNCTION_ARN

if [ -z "$FUNCTION_ARN" ]; then
    echo "Error: Function ARN is required"
    exit 1
fi

echo ""
echo "Step 2: Grant S3 permission to invoke Lambda"
echo "Adding Lambda resource-based policy..."

aws lambda add-permission \
    --function-name "$FUNCTION_ARN" \
    --statement-id S3InvokeFunction \
    --action "lambda:InvokeFunction" \
    --principal s3.amazonaws.com \
    --source-arn "arn:aws:s3:::$BUCKET" \
    --profile "$PROFILE" \
    --region "$REGION" || echo "Permission may already exist"

echo ""
echo "Step 3: Configure S3 bucket notification"
echo "Creating notification configuration..."

# Create notification configuration JSON
cat > /tmp/s3-notification.json <<EOF
{
    "LambdaFunctionConfigurations": [
        {
            "Id": "BooksUploadTrigger",
            "LambdaFunctionArn": "$FUNCTION_ARN",
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {
                            "Name": "prefix",
                            "Value": "books/"
                        },
                        {
                            "Name": "suffix",
                            "Value": ".zip"
                        }
                    ]
                }
            }
        }
    ]
}
EOF

echo "Applying notification configuration to S3 bucket..."
aws s3api put-bucket-notification-configuration \
    --bucket "$BUCKET" \
    --notification-configuration file:///tmp/s3-notification.json \
    --profile "$PROFILE"

rm /tmp/s3-notification.json

echo ""
echo "✅ S3 trigger configured successfully!"
echo ""
echo "Next steps:"
echo "1. Run the migration script to populate DynamoDB with existing books"
echo "2. Upload a test book to verify the trigger works"
echo ""
