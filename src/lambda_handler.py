"""Lambda handler for checking file existence in S3."""

import json
import logging

import boto3

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def check_file_exists(bucket: str, key: str) -> bool:
    """Check if a file exists in S3 bucket.

    Args:
        bucket: Name of the S3 bucket
        key: File key/path in the bucket

    Returns:
        bool: True if file exists, False otherwise
    """
    logger.info(f"Checking file existence: bucket={bucket}, key={key}")
    s3 = boto3.client("s3")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        logger.info("File exists")
        return True
    except Exception as e:
        logger.info(f"File does not exist: {str(e)}")
        return False


def lambda_handler(event: dict, context: dict) -> dict:
    """Lambda function to check if file exists in S3.

    Args:
        event: Lambda event containing bucket and file_key
        context: Lambda context object

    Returns:
        dict: Response object containing status code and result
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        bucket = event["bucket"]
        file_key = event["file_key"]
        logger.info(f"Processing request for bucket={bucket}, key={file_key}")

        exists = check_file_exists(bucket, file_key)

        response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"file_exists": exists, "bucket": bucket, "file_key": file_key}
            ),
        }
        logger.info(f"Returning response: {json.dumps(response)}")
        return response

    except KeyError as e:
        error_msg = f"Missing required field: {str(e)}"
        logger.error(error_msg)
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": error_msg}),
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": error_msg}),
        }
