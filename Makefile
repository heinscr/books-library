.PHONY: help init plan apply destroy output deploy-all deploy-infra deploy-backend deploy-frontend clean

# Default AWS profile (can be overridden)
AWS_PROFILE ?= default
AWS_REGION ?= us-east-2

# Colors for output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
NC     := \033[0m # No Color

help: ## Show this help message
	@echo 'Usage: make [target] [AWS_PROFILE=profile-name]'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ''
	@echo 'Examples:'
	@echo '  make init                    # Initialize Terraform'
	@echo '  make deploy-all              # Full deployment (infra + backend + frontend)'
	@echo '  make deploy-all AWS_PROFILE=craig-dev  # Use specific AWS profile'

init: ## Initialize Terraform
	@echo "$(YELLOW)Initializing Terraform...$(NC)"
	cd terraform && terraform init

plan: ## Show Terraform plan
	@echo "$(YELLOW)Planning Terraform changes...$(NC)"
	cd terraform && terraform plan

apply: ## Apply Terraform configuration
	@echo "$(YELLOW)Applying Terraform configuration...$(NC)"
	cd terraform && terraform apply
	@echo "$(GREEN)✓ Infrastructure created$(NC)"
	@echo ""
	@echo "$(YELLOW)Important outputs:$(NC)"
	@cd terraform && terraform output samconfig_parameters
	@cd terraform && terraform output frontend_config

destroy: ## Destroy all Terraform resources
	@echo "$(YELLOW)WARNING: This will destroy all infrastructure!$(NC)"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ]
	@echo "$(YELLOW)Emptying S3 buckets...$(NC)"
	-aws s3 rm s3://$$(cd terraform && terraform output -raw books_bucket_name) --recursive --profile $(AWS_PROFILE)
	-aws s3 rm s3://$$(cd terraform && terraform output -raw frontend_bucket_name) --recursive --profile $(AWS_PROFILE)
	@echo "$(YELLOW)Destroying Terraform resources...$(NC)"
	cd terraform && terraform destroy
	@echo "$(GREEN)✓ Infrastructure destroyed$(NC)"

output: ## Show Terraform outputs
	@cd terraform && terraform output

save-outputs: ## Save Terraform outputs to file
	@cd terraform && terraform output > ../terraform-outputs.txt
	@echo "$(GREEN)✓ Outputs saved to terraform-outputs.txt$(NC)"

deploy-infra: apply save-outputs ## Deploy infrastructure with Terraform
	@echo "$(GREEN)✓ Infrastructure deployment complete$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Update samconfig.toml with Terraform outputs"
	@echo "  2. Run: make deploy-backend"

deploy-backend: ## Build and deploy Lambda functions with SAM
	@echo "$(YELLOW)Building SAM application...$(NC)"
	sam build
	@echo "$(YELLOW)Deploying SAM application...$(NC)"
	sam deploy --profile $(AWS_PROFILE)
	@echo "$(GREEN)✓ Backend deployment complete$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Note the API Gateway URL from above"
	@echo "  2. Update frontend/config.js"
	@echo "  3. Run: make deploy-frontend"

configure-s3-trigger: ## Configure S3 trigger for Lambda
	@echo "$(YELLOW)Configuring S3 trigger...$(NC)"
	@export S3_BUCKET=$$(cd terraform && terraform output -raw books_bucket_name) && \
	export AWS_PROFILE=$(AWS_PROFILE) && \
	cd scripts && ./configure-s3-trigger.sh
	@echo "$(GREEN)✓ S3 trigger configured$(NC)"

deploy-frontend: ## Deploy frontend to S3
	@echo "$(YELLOW)Deploying frontend to S3...$(NC)"
	@FRONTEND_BUCKET=$$(cd terraform && terraform output -raw frontend_bucket_name) && \
	aws s3 sync frontend/ s3://$$FRONTEND_BUCKET/ --profile $(AWS_PROFILE) && \
	aws s3 sync docs/ s3://$$FRONTEND_BUCKET/api-docs/ --exclude "*.md" --profile $(AWS_PROFILE)
	@echo "$(GREEN)✓ Frontend deployment complete$(NC)"
	@echo ""
	@echo "$(YELLOW)Frontend URL:$(NC)"
	@cd terraform && terraform output frontend_bucket_website_url

deploy-all: deploy-infra deploy-backend configure-s3-trigger deploy-frontend ## Full deployment (infra, backend, frontend)
	@echo ""
	@echo "$(GREEN)========================================$(NC)"
	@echo "$(GREEN)✓ Complete deployment finished!$(NC)"
	@echo "$(GREEN)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Frontend URL:$(NC)"
	@cd terraform && terraform output frontend_bucket_website_url
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Create Cognito users: make create-admin-user"
	@echo "  2. Visit the frontend URL above"

create-admin-user: ## Create an admin user (interactive)
	@echo "$(YELLOW)Creating admin user...$(NC)"
	@read -p "Enter email address: " email && \
	read -s -p "Enter temporary password: " temp_pass && echo && \
	read -s -p "Enter permanent password: " perm_pass && echo && \
	USER_POOL_ID=$$(cd terraform && terraform output -raw cognito_user_pool_id) && \
	aws cognito-idp admin-create-user \
		--user-pool-id $$USER_POOL_ID \
		--username $$email \
		--temporary-password $$temp_pass \
		--profile $(AWS_PROFILE) && \
	aws cognito-idp admin-set-user-password \
		--user-pool-id $$USER_POOL_ID \
		--username $$email \
		--password $$perm_pass \
		--permanent \
		--profile $(AWS_PROFILE) && \
	aws cognito-idp create-group \
		--user-pool-id $$USER_POOL_ID \
		--group-name admins \
		--description "Administrators" \
		--profile $(AWS_PROFILE) 2>/dev/null || true && \
	aws cognito-idp admin-add-user-to-group \
		--user-pool-id $$USER_POOL_ID \
		--username $$email \
		--group-name admins \
		--profile $(AWS_PROFILE)
	@echo "$(GREEN)✓ Admin user created$(NC)"

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	pipenv run pytest tests/test_handler.py -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-coverage: ## Run tests with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	pipenv run pytest tests/test_handler.py --cov=gateway_backend.handler --cov-report=term-missing
	@echo "$(GREEN)✓ Tests complete$(NC)"

lint: ## Run linting
	@echo "$(YELLOW)Running linting...$(NC)"
	./scripts/lint.sh
	@echo "$(GREEN)✓ Linting complete$(NC)"

clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf .aws-sam/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf gateway_backend/__pycache__/
	rm -rf tests/__pycache__/
	rm -f terraform-outputs.txt
	@echo "$(GREEN)✓ Clean complete$(NC)"

update-frontend: ## Quick update frontend only
	@echo "$(YELLOW)Updating frontend...$(NC)"
	@if [ -d "terraform/.terraform" ]; then \
		FRONTEND_BUCKET=$$(cd terraform && terraform output -raw frontend_bucket_name) && \
		aws s3 sync frontend/ s3://$$FRONTEND_BUCKET/ --profile $(AWS_PROFILE) && \
		aws s3 sync docs/ s3://$$FRONTEND_BUCKET/api-docs/ --exclude "*.md" --profile $(AWS_PROFILE); \
	else \
		echo "$(YELLOW)Terraform not initialized. Use: make update-frontend FRONTEND_BUCKET=your-bucket$(NC)"; \
		if [ -z "$$FRONTEND_BUCKET" ]; then \
			echo "$(YELLOW)Error: FRONTEND_BUCKET not set$(NC)"; \
			exit 1; \
		fi; \
		aws s3 sync frontend/ s3://$$FRONTEND_BUCKET/books-app/ --profile $(AWS_PROFILE) && \
		aws s3 sync docs/ s3://$$FRONTEND_BUCKET/books-app/api-docs/ --exclude "*.md" --profile $(AWS_PROFILE); \
	fi
	@echo "$(GREEN)✓ Frontend updated$(NC)"

update-backend: ## Quick update backend only
	@echo "$(YELLOW)Updating backend...$(NC)"
	sam build
	sam deploy --profile $(AWS_PROFILE)
	@echo "$(GREEN)✓ Backend updated$(NC)"

status: ## Show deployment status
	@echo "$(YELLOW)Deployment Status$(NC)"
	@echo ""
	@echo "$(YELLOW)Terraform:$(NC)"
	@cd terraform && terraform workspace show 2>/dev/null && terraform output -json > /dev/null 2>&1 && echo "  ✓ Infrastructure deployed" || echo "  ✗ Infrastructure not deployed"
	@echo ""
	@echo "$(YELLOW)SAM:$(NC)"
	@sam list stack-outputs 2>/dev/null | grep -q ApiUrl && echo "  ✓ Backend deployed" || echo "  ✗ Backend not deployed"
	@echo ""
	@echo "$(YELLOW)Frontend:$(NC)"
	@FRONTEND_BUCKET=$$(cd terraform && terraform output -raw frontend_bucket_name 2>/dev/null) && \
	aws s3 ls s3://$$FRONTEND_BUCKET/index.html --profile $(AWS_PROFILE) >/dev/null 2>&1 && echo "  ✓ Frontend deployed" || echo "  ✗ Frontend not deployed"

info: ## Show important deployment information
	@echo "$(YELLOW)Deployment Information$(NC)"
	@echo ""
	@echo "$(YELLOW)S3 Buckets:$(NC)"
	@cd terraform && terraform output books_bucket_name 2>/dev/null || echo "  Not deployed"
	@cd terraform && terraform output frontend_bucket_name 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "$(YELLOW)Cognito:$(NC)"
	@cd terraform && terraform output cognito_user_pool_id 2>/dev/null || echo "  Not deployed"
	@cd terraform && terraform output cognito_client_id 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "$(YELLOW)Frontend URL:$(NC)"
	@cd terraform && terraform output frontend_bucket_website_url 2>/dev/null || echo "  Not deployed"
	@echo ""
	@echo "$(YELLOW)API Gateway:$(NC)"
	@sam list stack-outputs 2>/dev/null | grep ApiUrl | awk '{print "  " $$NF}' || echo "  Not deployed"
