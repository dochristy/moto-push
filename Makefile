.PHONY: help install test clean build deploy-local start-localstack stop-localstack invoke-local all format check-lambda

help:
	@echo "Available commands:"
	@echo "  make install         - Install all dependencies"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make build          - Build Lambda deployment package"
	@echo "  make deploy-local   - Deploy to LocalStack"
	@echo "  make invoke-local   - Test Lambda function locally"
	@echo "  make check-lambda   - Check Lambda function status and logs"
	@echo "  make all            - Run full local test cycle"
	@echo "  make format         - Format code using black"

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:
	python -m pytest tests/ -v

format:
	black src/ tests/
	isort src/ tests/

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	rm -f lambda_function.zip
	rm -f output.json
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

build: clean
	mkdir -p dist
	cp -r src/* dist/
	cd dist && pip install -r ../requirements.txt -t .
	cd dist && zip -r ../lambda_function.zip .

create-test-bucket:
	@echo "Creating test bucket and file..."
	awslocal s3 mb s3://test-bucket || true
	echo "test content" | awslocal s3 cp - s3://test-bucket/test-file.txt

check-lambda:
	@echo "Checking Lambda function configuration..."
	awslocal lambda get-function --function-name test-lambda
	@echo "\nChecking Lambda function logs..."
	@LOG_STREAMS=$(awslocal logs describe-log-streams --log-group-name /aws/lambda/test-lambda --query 'logStreams[0].logStreamName' --output text 2>/dev/null); \
	if [ "$?" -eq "0" ] && [ "$LOG_STREAMS" != "None" ]; then \
		awslocal logs get-log-events \
			--log-group-name /aws/lambda/test-lambda \
			--log-stream-name "$LOG_STREAMS" \
			--limit 10; \
	else \
		echo "No log streams found yet."; \
	fi

deploy-local: build create-test-bucket
	@echo "Deploying Lambda function..."
	awslocal lambda delete-function --function-name test-lambda || true
	sleep 2
	awslocal lambda create-function \
		--function-name test-lambda \
		--runtime python3.9 \
		--handler lambda_handler.lambda_handler \
		--zip-file fileb://lambda_function.zip \
		--role arn:aws:iam::123456789012:role/lambda-role \
		--timeout 30 \
		--memory-size 128
	@echo "Waiting for function to be active..."
	@for i in $(seq 1 30); do \
		STATUS=$(awslocal lambda get-function --function-name test-lambda --query 'Configuration.State' --output text); \
		if [ "$STATUS" = "Active" ]; then \
			echo "Function is active!"; \
			break; \
		elif [ "$STATUS" = "Failed" ]; then \
			echo "Function deployment failed!"; \
			awslocal lambda get-function --function-name test-lambda; \
			exit 1; \
		fi; \
		echo "Status: $STATUS. Waiting..."; \
		sleep 2; \
	done
	@echo "Waiting for Lambda function to be ready..."
	sleep 5
	@$(MAKE) check-lambda

invoke-local:
	@echo "Invoking Lambda function..."
	awslocal lambda invoke \
		--function-name test-lambda \
		--payload '{"bucket": "test-bucket", "file_key": "test-file.txt"}' \
		--log-type Tail \
		output.json > lambda_response.json
	@echo "\nFunction response:"
	@cat output.json
	@echo "\nFunction logs:"
	@cat lambda_response.json | jq -r '.LogResult' | base64 -d || echo "No logs available"

wait-for-logs:
	@echo "Waiting for logs to be available..."
	@sleep 5  # Give some time for logs to appear
	@LATEST_STREAM=$(awslocal logs describe-log-streams \
		--log-group-name /aws/lambda/test-lambda \
		--order-by LastEventTime \
		--descending \
		--max-items 1 \
		--query 'logStreams[0].logStreamName' \
		--output text 2>/dev/null || echo ""); \
	if [ ! -z "$LATEST_STREAM" ] && [ "$LATEST_STREAM" != "None" ]; then \
		awslocal logs get-log-events \
			--log-group-name /aws/lambda/test-lambda \
			--log-stream-name "$LATEST_STREAM" \
			--limit 10 \
			--query 'events[].message' \
			--output text; \
	else \
		echo "No logs available yet"; \
	fi

start-localstack:
	docker stop localstack || true
	docker rm localstack || true
	docker run -d --name localstack \
		-p 4566:4566 -p 4510-4559:4510-4559 \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-e LAMBDA_EXECUTOR=docker \
		-e DOCKER_HOST=unix:///var/run/docker.sock \
		-e DEBUG=1 \
		-e AWS_DEFAULT_REGION=us-east-1 \
		-e SERVICES=lambda,s3,logs,iam \
		-e LS_LOG=debug \
		-e EAGER_SERVICE_LOADING=1 \
		localstack/localstack
	@echo "Waiting for LocalStack to start..."
	@sleep 15

stop-localstack:
	docker stop localstack || true
	docker rm localstack || true

check-s3:
	@echo "\nChecking S3:"
	awslocal s3 ls s3://test-bucket/
	@echo "\nFile content:"
	awslocal s3 cp s3://test-bucket/test-file.txt -

test-nonexistent:
	@echo "\nTesting with non-existent file..."
	awslocal lambda invoke \
		--function-name test-lambda \
		--payload '{"bucket": "test-bucket", "file_key": "nonexistent.txt"}' \
		--log-type Tail \
		output.json > lambda_response.json
	@echo "Function response:"
	@cat output.json
	@echo "\nFunction logs:"
	@cat lambda_response.json | jq -r '.LogResult' | base64 -d || echo "No logs available"

all: install test start-localstack deploy-local invoke-local check-s3 test-nonexistent