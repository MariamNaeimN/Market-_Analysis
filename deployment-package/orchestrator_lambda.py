import json
import boto3
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Initialize AWS clients
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
bedrock_runtime = boto3.client('bedrock-runtime')
lambda_client = boto3.client('lambda')
cloudwatch = boto3.client('cloudwatch')
sns_client = boto3.client('sns')

# Environment variables
PARSER_LAMBDA_ARN = os.environ['PARSER_LAMBDA_ARN']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
ENVIRONMENT = os.environ['ENVIRONMENT']

# Constants
SUPPORTED_FORMATS = []  # Empty list means all formats are supported
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SYNC_THRESHOLD_MB = 1
SYNC_THRESHOLD_BYTES = SYNC_THRESHOLD_MB * 1024 * 1024
MAX_RETRIES = 3
BEDROCK_MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'
BEDROCK_TIMEOUT = 30

def lambda_handler(event, context):
    """Main Lambda handler for S3 event notifications"""
    job_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Parse S3 event
        s3_event = parse_s3_event(event)
        bucket = s3_event['bucket']
        key = s3_event['key']
        
        log_info(f"Processing job {job_id}: s3://{bucket}/{key}")
        
        # Validate file format and size
        validate_file(bucket, key)
        
        # Extract text using Textract
        extracted_text = extract_text_with_textract(bucket, key, job_id)
        
        # Analyze with Bedrock
        analysis_results = analyze_with_bedrock(extracted_text, job_id)
        
        # Invoke Parser Lambda
        invoke_parser_lambda(analysis_results, bucket, key, job_id)
        
        # Emit success metrics
        duration = time.time() - start_time
        emit_metrics(job_id, 'Success', duration)
        
        log_info(f"Job {job_id} completed successfully in {duration:.2f}s")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'jobId': job_id,
                'status': 'completed',
                'duration': duration
            })
        }
        
    except Exception as e:
        duration = time.time() - start_time
        error_type = type(e).__name__
        error_message = str(e)
        
        log_error(f"Job {job_id} failed: {error_type} - {error_message}")
        emit_metrics(job_id, 'Failure', duration, error_type)
        publish_critical_error(job_id, error_type, error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'jobId': job_id,
                'status': 'failed',
                'error': error_message
            })
        }

def parse_s3_event(event: Dict[str, Any]) -> Dict[str, str]:
    """Parse S3 event notification payload"""
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        return {'bucket': bucket, 'key': key}
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid S3 event format: {e}")

def validate_file(bucket: str, key: str) -> None:
    """Validate file format and size"""
    # Check file extension (accept all formats if SUPPORTED_FORMATS is empty)
    file_ext = os.path.splitext(key)[1].lower()
    if SUPPORTED_FORMATS and file_ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported file format: {file_ext}. Supported formats: {SUPPORTED_FORMATS}")
    
    # Check file size
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = response['ContentLength']
        
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size {file_size / 1024 / 1024:.2f}MB exceeds maximum {MAX_FILE_SIZE_MB}MB")
        
        log_info(f"File validation passed: {file_ext}, {file_size / 1024 / 1024:.2f}MB")
    except Exception as e:
        raise ValueError(f"Failed to validate file: {e}")

def extract_text_with_textract(bucket: str, key: str, job_id: str) -> str:
    """Extract text from documents. Textract for supported formats, direct S3 read for others."""
    file_ext = os.path.splitext(key)[1].lower()
    
    # Textract-supported formats
    textract_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif']
    
    if file_ext in textract_formats:
        # Use Textract: sync for small files, async for large
        response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = response['ContentLength']
        
        try:
            if file_size <= SYNC_THRESHOLD_BYTES:
                return extract_text_sync(bucket, key, job_id)
            else:
                return extract_text_async(bucket, key, job_id)
        except Exception as e:
            # Sync failed — try async as fallback for PDFs
            if 'UnsupportedDocument' in str(e) and file_size <= SYNC_THRESHOLD_BYTES:
                log_warning(f"Job {job_id}: Sync Textract failed, trying async")
                try:
                    return extract_text_async(bucket, key, job_id)
                except Exception as e2:
                    log_warning(f"Job {job_id}: Async Textract also failed: {e2}")
            else:
                log_warning(f"Job {job_id}: Textract failed: {e}")
            
            # Last resort: read raw file content
            log_warning(f"Job {job_id}: Falling back to raw file read")
            return _read_raw_from_s3(bucket, key, job_id)
    else:
        # Non-Textract format: read directly from S3
        log_info(f"Job {job_id}: File type {file_ext} not supported by Textract, reading from S3")
        return _read_raw_from_s3(bucket, key, job_id)


def _read_raw_from_s3(bucket: str, key: str, job_id: str) -> str:
    """Read file content directly from S3 as text."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        raw = response['Body'].read()
        # Try UTF-8 first, fall back to latin-1
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('latin-1', errors='ignore')
        log_info(f"Job {job_id}: Read {len(text)} characters from S3")
        return text
    except Exception as e:
        raise Exception(f"Failed to read file from S3: {e}")

def extract_text_sync(bucket: str, key: str, job_id: str) -> str:
    """Synchronous text extraction for files <= 1MB"""
    log_info(f"Job {job_id}: Using synchronous Textract")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = textract_client.detect_document_text(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}}
            )
            
            # Extract text from blocks
            text_blocks = [
                block['Text'] 
                for block in response.get('Blocks', []) 
                if block['BlockType'] == 'LINE'
            ]
            
            extracted_text = '\n'.join(text_blocks)
            
            if not extracted_text.strip():
                log_warning(f"Job {job_id}: No text extracted from document")
                return ""
            
            log_info(f"Job {job_id}: Extracted {len(extracted_text)} characters")
            return extracted_text
            
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait_time = exponential_backoff(attempt)
                log_warning(f"Job {job_id}: Textract attempt {attempt} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise Exception(f"Textract sync extraction failed after {MAX_RETRIES} attempts: {e}")

def extract_text_async(bucket: str, key: str, job_id: str) -> str:
    """Asynchronous text extraction for files > 1MB"""
    log_info(f"Job {job_id}: Using asynchronous Textract")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Start async job
            response = textract_client.start_document_text_detection(
                DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}}
            )
            textract_job_id = response['JobId']
            log_info(f"Job {job_id}: Started Textract job {textract_job_id}")
            
            # Poll for completion
            extracted_text = poll_textract_job(textract_job_id, job_id)
            return extracted_text
            
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait_time = exponential_backoff(attempt)
                log_warning(f"Job {job_id}: Textract attempt {attempt} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise Exception(f"Textract async extraction failed after {MAX_RETRIES} attempts: {e}")

def poll_textract_job(textract_job_id: str, job_id: str) -> str:
    """Poll Textract async job until completion"""
    max_poll_attempts = 60  # 5 minutes with 5s intervals
    poll_interval = 5
    
    for poll_attempt in range(max_poll_attempts):
        try:
            response = textract_client.get_document_text_detection(JobId=textract_job_id)
            status = response['JobStatus']
            
            if status == 'SUCCEEDED':
                # Extract text from blocks
                text_blocks = [
                    block['Text'] 
                    for block in response.get('Blocks', []) 
                    if block['BlockType'] == 'LINE'
                ]
                
                # Handle pagination
                next_token = response.get('NextToken')
                while next_token:
                    response = textract_client.get_document_text_detection(
                        JobId=textract_job_id,
                        NextToken=next_token
                    )
                    text_blocks.extend([
                        block['Text'] 
                        for block in response.get('Blocks', []) 
                        if block['BlockType'] == 'LINE'
                    ])
                    next_token = response.get('NextToken')
                
                extracted_text = '\n'.join(text_blocks)
                
                if not extracted_text.strip():
                    log_warning(f"Job {job_id}: No text extracted from document")
                    return ""
                
                log_info(f"Job {job_id}: Extracted {len(extracted_text)} characters")
                return extracted_text
                
            elif status == 'FAILED':
                raise Exception(f"Textract job failed: {response.get('StatusMessage', 'Unknown error')}")
            
            elif status == 'IN_PROGRESS':
                log_info(f"Job {job_id}: Textract job in progress, polling attempt {poll_attempt + 1}")
                time.sleep(poll_interval)
            
            else:
                raise Exception(f"Unexpected Textract job status: {status}")
                
        except Exception as e:
            if poll_attempt < max_poll_attempts - 1:
                time.sleep(poll_interval)
            else:
                raise Exception(f"Textract polling failed: {e}")
    
    raise Exception(f"Textract job timed out after {max_poll_attempts * poll_interval}s")

def analyze_with_bedrock(text: str, job_id: str) -> Dict[str, Any]:
    """Analyze market intelligence documents using AWS Bedrock"""
    log_info(f"Job {job_id}: Starting Bedrock analysis")
    
    # Construct analysis prompt
    analysis_instruction = """Analyze the following document (competitor report, news feed, or market document) and extract structured market intelligence in JSON format.

Please identify and extract:
1. Competitors mentioned (company names and their roles/positions in the market)
2. Key dates (product launches, announcements, events, report dates)
3. Financial information (revenue, funding, pricing, market share, valuations)
4. Strategic initiatives (partnerships, acquisitions, product launches, market expansions)
5. Market risks and opportunities (competitive threats, market trends, regulatory changes)

Return the analysis as a JSON object with the following structure:
{
  "parties": [
    {"name": "Company/Competitor Name", "role": "Market Position/Role"}
  ],
  "dates": {
    "effectiveDate": "YYYY-MM-DD or null (primary date of document/event)",
    "terminationDate": "YYYY-MM-DD or null (end date if applicable)",
    "keyDates": [
      {"date": "YYYY-MM-DD", "event": "Description of the event or milestone"}
    ]
  },
  "paymentTerms": [
    {"description": "Financial metric description (revenue, funding, pricing, etc.)", "amount": "Amount with currency or null"}
  ],
  "obligations": [
    {"party": "Company Name", "obligation": "Strategic initiative or commitment"}
  ],
  "risks": [
    {"type": "Risk or Opportunity", "riskType": "Category such as Regulatory, Competition, Financial, Technology, Market, Operational, etc.", "severity": "High/Medium/Low (for risks only)", "potential": "High/Medium/Low (for opportunities only)", "description": "Detailed description of market risk or opportunity"}
  ]
}

If any information is not found, use null or empty arrays as appropriate. Focus on extracting actionable market intelligence. IMPORTANT: Only extract information that is explicitly stated in the document. Do not infer, estimate, or generate any data that is not directly present in the text. If a value is not clearly stated, use null."""
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Build message content
            content = f"{analysis_instruction}\n\nDocument Text:\n{text[:50000]}"
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.0
            }
            
            response = bedrock_runtime.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Extract JSON from response
            analysis_results = extract_json_from_text(content)
            
            log_info(f"Job {job_id}: Bedrock analysis completed")
            return analysis_results
            
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait_time = exponential_backoff(attempt)
                log_warning(f"Job {job_id}: Bedrock attempt {attempt} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise Exception(f"Bedrock analysis failed after {MAX_RETRIES} attempts: {e}")

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON object from text that may contain markdown or other formatting"""
    # Try to find JSON in code blocks
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        json_str = text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        json_str = text[start:end].strip()
    else:
        # Try to find JSON object directly
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
        else:
            json_str = text
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from Bedrock response: {e}")

def invoke_parser_lambda(analysis_results: Dict[str, Any], bucket: str, key: str, job_id: str) -> None:
    """Invoke Parser Lambda with analysis results"""
    log_info(f"Job {job_id}: Invoking Parser Lambda")
    
    payload = {
        'jobId': job_id,
        'analysisResults': analysis_results,
        'metadata': {
            'bucket': bucket,
            'key': key,
            'timestamp': datetime.utcnow().isoformat()
        }
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = lambda_client.invoke(
                FunctionName=PARSER_LAMBDA_ARN,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Check response
            response_payload = json.loads(response['Payload'].read())
            
            if response['StatusCode'] != 200:
                raise Exception(f"Parser Lambda returned status {response['StatusCode']}")
            
            if 'errorMessage' in response_payload:
                raise Exception(f"Parser Lambda error: {response_payload['errorMessage']}")
            
            log_info(f"Job {job_id}: Parser Lambda invoked successfully")
            return
            
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait_time = exponential_backoff(attempt)
                log_warning(f"Job {job_id}: Parser Lambda attempt {attempt} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise Exception(f"Parser Lambda invocation failed after {MAX_RETRIES} attempts: {e}")

def exponential_backoff(attempt: int) -> float:
    """Calculate exponential backoff delay"""
    return min(2 ** attempt, 32)  # Max 32 seconds

def emit_metrics(job_id: str, status: str, duration: float, error_type: Optional[str] = None) -> None:
    """Emit custom CloudWatch metrics"""
    try:
        metrics = [
            {
                'MetricName': 'JobSuccessRate',
                'Value': 1.0 if status == 'Success' else 0.0,
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'ProcessingDuration',
                'Value': duration,
                'Unit': 'Seconds',
                'Timestamp': datetime.utcnow()
            }
        ]
        
        if error_type:
            metrics.append({
                'MetricName': 'ErrorCount',
                'Value': 1.0,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {'Name': 'ErrorType', 'Value': error_type}
                ]
            })
        
        cloudwatch.put_metric_data(
            Namespace=f'ContractAnalysisPipeline/{ENVIRONMENT}',
            MetricData=metrics
        )
    except Exception as e:
        log_error(f"Failed to emit metrics: {e}")

def publish_critical_error(job_id: str, error_type: str, error_message: str) -> None:
    """Publish critical error to SNS topic"""
    try:
        message = {
            'jobId': job_id,
            'errorType': error_type,
            'errorMessage': error_message,
            'timestamp': datetime.utcnow().isoformat(),
            'environment': ENVIRONMENT
        }
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f'Contract Analysis Pipeline Critical Error - {ENVIRONMENT}',
            Message=json.dumps(message, indent=2)
        )
    except Exception as e:
        log_error(f"Failed to publish SNS notification: {e}")

def log_info(message: str) -> None:
    """Log info message"""
    print(f"[INFO] {message}")

def log_warning(message: str) -> None:
    """Log warning message"""
    print(f"[WARNING] {message}")

def log_error(message: str) -> None:
    """Log error message"""
    print(f"[ERROR] {message}")
