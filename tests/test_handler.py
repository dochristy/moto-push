"""Test module for lambda_handler."""

import json
import os

import boto3
import pytest
from moto import mock_aws

from src.lambda_handler import check_file_exists, lambda_handler


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def s3_client(aws_credentials):
    """Create a mocked S3 client."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        yield s3


@pytest.fixture
def test_bucket(s3_client):
    """Create a test bucket with a sample file."""
    bucket_name = "test-bucket"
    file_key = "test-file.txt"

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body="test content")

    return {"bucket": bucket_name, "file_key": file_key}


def test_check_file_exists(s3_client, test_bucket):
    """Test the check_file_exists function."""
    # Test file exists
    assert check_file_exists(test_bucket["bucket"], test_bucket["file_key"]) is True

    # Test file doesn't exist
    assert check_file_exists(test_bucket["bucket"], "nonexistent.txt") is False


def test_lambda_handler_success(s3_client, test_bucket):
    """Test successful lambda handler execution."""
    # Test with existing file
    response = lambda_handler(test_bucket, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["file_exists"] is True
    assert body["bucket"] == test_bucket["bucket"]
    assert body["file_key"] == test_bucket["file_key"]

    # Test with non-existing file
    event = test_bucket.copy()
    event["file_key"] = "nonexistent.txt"
    response = lambda_handler(event, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["file_exists"] is False


def test_lambda_handler_missing_params():
    """Test lambda handler with missing parameters."""
    # Test with missing bucket
    response = lambda_handler({"file_key": "test.txt"}, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])

    # Test with missing file_key
    response = lambda_handler({"bucket": "test-bucket"}, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])

    # Test with empty event
    response = lambda_handler({}, None)
    assert response["statusCode"] == 400
    assert "error" in json.loads(response["body"])
