# tests/test_handler.py

import pytest
import boto3
from moto import mock_aws
from src.lambda_handler import lambda_handler, check_file_exists

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto"""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'

@pytest.fixture
def s3_client(aws_credentials):
    with mock_aws():
        yield boto3.client('s3', region_name='us-east-1')

def test_check_file_exists(s3_client):
    # Create a bucket and put a file in it
    bucket_name = 'test-bucket'
    file_key = 'test-file.txt'

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body='test content')

    # Test file exists
    assert check_file_exists(bucket_name, file_key) == True

    # Test file doesn't exist
    assert check_file_exists(bucket_name, 'nonexistent.txt') == False

def test_lambda_handler(s3_client):
    # Create a bucket and put a file in it
    bucket_name = 'test-bucket'
    file_key = 'test-file.txt'

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Key=file_key, Body='test content')

    # Test with existing file
    event = {
        'bucket': bucket_name,
        'file_key': file_key
    }
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    assert 'file_exists' in response['body']

    # Test with non-existing file
    event['file_key'] = 'nonexistent.txt'
    response = lambda_handler(event, None)

    assert response['statusCode'] == 200
    assert 'file_exists' in response['body']

def test_lambda_handler_error():
    # Test with invalid event
    event = {}
    response = lambda_handler(event, None)

    assert response['statusCode'] == 500
    assert 'error' in response['body']