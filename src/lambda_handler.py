# src/lambda_handler.py

import boto3
import json

def check_file_exists(bucket, key):
    """Check if a file exists in S3 bucket"""
    s3 = boto3.client('s3')
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except:
        return False

def lambda_handler(event, context):
    """Lambda function to check if file exists in S3"""
    try:
        bucket = event['bucket']
        file_key = event['file_key']

        exists = check_file_exists(bucket, file_key)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'file_exists': exists,
                'bucket': bucket,
                'file_key': file_key
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }