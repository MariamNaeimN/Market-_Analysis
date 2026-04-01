import json
import boto3
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('logs')

# Environment variables
DYNAMODB_TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Get DynamoDB table
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

# Required fields for validation
REQUIRED_FIELDS = ['parties', 'dates', 'paymentTerms', 'obligations', 'risks']

def lambda_handler(event, context):
    """Main Lambda handler for parsing Bedrock output"""
    job_id = event.get('jobId', str(uuid.uuid4()))
    
    try:
        log_info(f"Parser job {job_id}: Starting processing")
        
        # Extract analysis results and metadata
        analysis_results = event.get('analysisResults', {})
        metadata = event.get('metadata', {})
        
        # Validate JSON structure
        validate_json_structure(analysis_results, job_id)
        
        # Transform data to DynamoDB schema
        transformed_data = transform_to_dynamodb_schema(
            analysis_results, 
            metadata, 
            job_id
        )
        
        # Write to DynamoDB
        write_to_dynamodb(transformed_data, job_id)
        
        log_info(f"Parser job {job_id}: Completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'jobId': job_id,
                'status': 'completed',
                'insightId': transformed_data['insightId']
            })
        }
        
    except ValidationError as e:
        error_message = str(e)
        log_error(f"Parser job {job_id}: Validation error - {error_message}")
        
        return {
            'statusCode': 400,
            'body': json.dumps({
                'jobId': job_id,
                'status': 'validation_failed',
                'error': error_message,
                'errorType': 'ValidationError'
            })
        }
        
    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        log_error(f"Parser job {job_id}: {error_type} - {error_message}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'jobId': job_id,
                'status': 'failed',
                'error': error_message,
                'errorType': error_type
            })
        }

def validate_json_structure(analysis_results: Dict[str, Any], job_id: str) -> None:
    """
    Validate Bedrock output JSON structure.
    Requirements: 5.1, 5.3
    """
    log_info(f"Parser job {job_id}: Validating JSON structure")
    
    # Check if analysis_results is a dictionary
    if not isinstance(analysis_results, dict):
        raise ValidationError(
            f"Analysis results must be a dictionary, got {type(analysis_results).__name__}"
        )
    
    # Check for required fields
    missing_fields = []
    for field in REQUIRED_FIELDS:
        if field not in analysis_results:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    # Validate field types
    if not isinstance(analysis_results.get('parties'), list):
        raise ValidationError("Field 'parties' must be a list")
    
    if not isinstance(analysis_results.get('dates'), dict):
        raise ValidationError("Field 'dates' must be a dictionary")
    
    if not isinstance(analysis_results.get('paymentTerms'), (list, dict)):
        raise ValidationError("Field 'paymentTerms' must be a list or dictionary")
    
    if not isinstance(analysis_results.get('obligations'), list):
        raise ValidationError("Field 'obligations' must be a list")
    
    if not isinstance(analysis_results.get('risks'), list):
        raise ValidationError("Field 'risks' must be a list")
    
    log_info(f"Parser job {job_id}: JSON validation passed")

def transform_to_dynamodb_schema(
    analysis_results: Dict[str, Any], 
    metadata: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:
    """
    Transform Bedrock output to DynamoDB schema format.
    Requirements: 5.2, 5.4
    """
    log_info(f"Parser job {job_id}: Transforming data to DynamoDB schema")
    
    # Generate unique insight ID
    insight_id = str(uuid.uuid4())
    
    # Extract document identifier from S3 key
    s3_key = metadata.get('key', '')
    document_id = extract_document_id(s3_key)
    
    # Get processing timestamp
    processing_timestamp = int(datetime.utcnow().timestamp())
    
    # Extract party names for indexing
    parties = analysis_results.get('parties', [])
    party_name = extract_primary_party_name(parties)
    
    # Extract effective date for indexing (must be a string for GSI key, never None/null)
    dates = analysis_results.get('dates', {})
    effective_date = dates.get('effectiveDate') or 'unknown'
    
    # Build DynamoDB item
    item = {
        'insightId': insight_id,
        'documentId': document_id,
        'uploadTimestamp': processing_timestamp,
        'partyName': party_name,
        'effectiveDate': effective_date,
        'jobId': job_id,
        'analysisResults': analysis_results,
        's3Metadata': {
            'bucket': metadata.get('bucket', ''),
            'key': s3_key,
            'uploadTime': metadata.get('timestamp', '')
        },
        'processingTimestamp': datetime.utcnow().isoformat(),
        'environment': ENVIRONMENT
    }
    
    log_info(f"Parser job {job_id}: Transformation completed")
    
    return item

def extract_document_id(s3_key: str) -> str:
    """Extract document identifier from S3 key"""
    # Remove file extension and path
    filename = s3_key.split('/')[-1]
    document_id = filename.rsplit('.', 1)[0] if '.' in filename else filename
    return document_id or 'unknown'

def extract_primary_party_name(parties: List[Dict[str, Any]]) -> str:
    """Extract primary party name for indexing"""
    if not parties or not isinstance(parties, list):
        return 'unknown'
    
    # Get first party name
    first_party = parties[0]
    if isinstance(first_party, dict):
        return first_party.get('name', 'unknown')
    elif isinstance(first_party, str):
        return first_party
    
    return 'unknown'

def write_to_dynamodb(item: Dict[str, Any], job_id: str) -> None:
    """
    Write structured insights to DynamoDB table.
    Requirements: 5.5, 6.1
    """
    log_info(f"Parser job {job_id}: Writing to DynamoDB")
    
    try:
        # Write item to DynamoDB
        table.put_item(Item=item)
        
        log_info(
            f"Parser job {job_id}: Successfully wrote insight {item['insightId']} "
            f"for document {item['documentId']}"
        )
        
    except Exception as e:
        error_message = f"DynamoDB write failed: {str(e)}"
        log_error(f"Parser job {job_id}: {error_message}")
        raise DynamoDBWriteError(error_message)

def log_info(message: str) -> None:
    """Log info message to CloudWatch"""
    print(f"[INFO] {message}")

def log_error(message: str) -> None:
    """Log error message to CloudWatch"""
    print(f"[ERROR] {message}")

# Custom exceptions
class ValidationError(Exception):
    """Raised when JSON validation fails"""
    pass

class DynamoDBWriteError(Exception):
    """Raised when DynamoDB write operation fails"""
    pass
