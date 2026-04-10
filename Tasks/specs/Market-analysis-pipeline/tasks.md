# Implementation Plan: Contract Analysis Pipeline

## Overview

This implementation plan creates a serverless contract analysis pipeline using AWS CloudFormation. The infrastructure includes S3 for document storage, Lambda functions for orchestration and parsing, AWS Textract for text extraction, AWS Bedrock for AI analysis, and DynamoDB for storing insights. All components are defined as infrastructure-as-code with proper IAM roles, security configurations, and monitoring.

## Tasks

- [x] 1. Create CloudFormation template structure and parameters
  - Create main CloudFormation template file (template.yaml)
  - Define parameters for environment-specific values (bucket names, table names, environment)
  - Define parameter constraints and default values
  - Add template metadata and description
  - _Requirements: 7.6_

- [x] 2. Define S3 bucket resource with security and lifecycle policies
  - [x] 2.1 Create S3 bucket resource with encryption configuration
    - Define S3 bucket with KMS encryption at rest
    - Configure bucket to block all public access
    - Add bucket versioning configuration
    - _Requirements: 1.2, 1.4, 9.1, 9.5_
  
  - [x] 2.2 Add S3 event notification configuration
    - Configure ObjectCreated event notification to trigger Orchestrator Lambda
    - Add event filter for supported file types (PDF, PNG, JPEG, TIFF)
    - Add event filter to reject files larger than 10MB
    - _Requirements: 1.1, 1.2, 1.3, 7.1_
  
  - [x] 2.3 Configure S3 lifecycle policies for cost optimization
    - Add lifecycle rule to transition objects to Glacier after 90 days
    - Configure lifecycle policy for processed documents
    - _Requirements: 10.2_

- [x] 3. Define DynamoDB table with indexes and encryption
  - [x] 3.1 Create DynamoDB table resource
    - Define table with unique identifier as partition key
    - Configure on-demand billing mode
    - Enable KMS encryption at rest
    - Add TTL configuration if needed
    - _Requirements: 6.1, 6.4, 9.2, 10.3_
  
  - [x] 3.2 Configure DynamoDB indexes
    - Create GSI for document identifier queries
    - Create GSI for upload timestamp queries
    - Create GSI for contract party name queries
    - Create GSI for date range queries
    - _Requirements: 6.2, 6.3_

- [ ] 4. Create IAM roles and policies for Lambda functions
  - [x] 4.1 Define Orchestrator Lambda IAM role
    - Create IAM role with Lambda service principal
    - Add policy for S3 read access to contract bucket
    - Add policy for Textract service access (StartDocumentTextDetection, GetDocumentTextDetection)
    - Add policy for Bedrock service access (InvokeModel)
    - Add policy for Lambda invoke permission (to call Parser Lambda)
    - Add policy for CloudWatch Logs write access
    - Add policy for CloudWatch Metrics put access
    - Add policy for SNS publish access
    - _Requirements: 7.2, 7.4, 9.4_
  
  - [x] 4.2 Define Parser Lambda IAM role
    - Create IAM role with Lambda service principal
    - Add policy for DynamoDB write access to insights table
    - Add policy for CloudWatch Logs write access
    - _Requirements: 7.2, 9.4_

- [x] 5. Implement Orchestrator Lambda function
  - [x] 5.1 Create Orchestrator Lambda resource in CloudFormation
    - Define Lambda function resource with runtime configuration
    - Configure memory allocation and timeout (5 minutes minimum)
    - Set environment variables for Textract, Bedrock, and Parser Lambda ARNs
    - Attach IAM role from task 4.1
    - Configure retry policy with exponential backoff
    - _Requirements: 7.2, 10.4_
  
  - [x] 5.2 Implement S3 event handler logic
    - Parse S3 event notification payload
    - Extract bucket name and object key
    - Validate file format and size
    - Initialize job tracking with unique identifier
    - _Requirements: 1.1, 2.2_
  
  - [x] 5.3 Implement Textract integration
    - Check document size to determine sync vs async processing
    - For documents > 1MB, use StartDocumentTextDetection (async)
    - For documents ≤ 1MB, use DetectDocumentText (sync)
    - Poll for async job completion with exponential backoff
    - Handle Textract errors and update job status
    - _Requirements: 2.1, 2.3, 3.1, 3.2, 3.3, 3.4, 10.1_
  
  - [x] 5.4 Implement Bedrock integration
    - Construct prompt for contract analysis with extracted text
    - Invoke Bedrock model with structured output format
    - Request identification of parties, dates, terms, obligations, and risks
    - Set timeout to 30 seconds for contracts up to 50 pages
    - Handle Bedrock errors and update job status
    - _Requirements: 2.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [x] 5.5 Implement Parser Lambda invocation
    - Invoke Parser Lambda with Bedrock analysis results
    - Pass document metadata and job identifier
    - Handle Parser Lambda errors
    - Update job status to complete on success
    - _Requirements: 2.5_
  
  - [x] 5.6 Implement error handling and retry logic
    - Add try-catch blocks for all AWS service calls
    - Implement exponential backoff for transient failures
    - Retry failed operations up to 3 times
    - Mark job as permanently failed after 3 retries
    - Log all errors to CloudWatch with contextual information
    - Publish critical errors to SNS topic
    - _Requirements: 2.3, 8.1, 8.2, 8.3, 8.5_
  
  - [x] 5.7 Implement CloudWatch metrics emission
    - Emit custom metric for job success rate
    - Emit custom metric for processing duration
    - Emit custom metric for error counts by type
    - _Requirements: 8.4_

- [x] 6. Implement Parser Lambda function
  - [x] 6.1 Create Parser Lambda resource in CloudFormation
    - Define Lambda function resource with runtime configuration
    - Configure memory allocation and timeout
    - Set environment variables for DynamoDB table name
    - Attach IAM role from task 4.2
    - _Requirements: 7.2, 10.4_
  
  - [x] 6.2 Implement JSON validation logic
    - Validate Bedrock output JSON structure
    - Check for required fields (parties, dates, terms, obligations, risks)
    - Handle malformed JSON with structured error response
    - Log validation errors to CloudWatch
    - _Requirements: 5.1, 5.3_
  
  - [x] 6.3 Implement data transformation logic
    - Transform Bedrock output to DynamoDB schema format
    - Enrich output with processing timestamp
    - Enrich output with document identifier
    - Enrich output with S3 object metadata
    - _Requirements: 5.2, 5.4_
  
  - [x] 6.4 Implement DynamoDB write operation
    - Write structured insights to DynamoDB table
    - Use unique identifier as partition key
    - Handle DynamoDB write errors
    - Log successful writes to CloudWatch
    - _Requirements: 5.5, 6.1_

- [x] 7. Create SNS topic for critical error notifications
  - Define SNS topic resource
  - Configure topic policy for Lambda publish access
  - Add email subscription endpoint (parameterized)
  - _Requirements: 8.5_

- [ ] 8. Configure CloudWatch Logs and monitoring
  - [ ] 8.1 Create CloudWatch Log Groups
    - Define log group for Orchestrator Lambda
    - Define log group for Parser Lambda
    - Configure log retention period (30 days)
    - _Requirements: 8.1_
  
  - [ ] 8.2 Enable CloudTrail logging
    - Configure CloudTrail to log S3 data events
    - Configure CloudTrail to log DynamoDB data events
    - Configure CloudTrail to log Lambda invocations
    - _Requirements: 9.6_

- [ ] 9. Add CloudFormation outputs
  - Output S3 bucket name
  - Output DynamoDB table name
  - Output Orchestrator Lambda ARN
  - Output Parser Lambda ARN
  - Output SNS topic ARN
  - _Requirements: 7.5_

- [ ] 10. Create deployment documentation
  - Document CloudFormation stack deployment command
  - Document required parameter values
  - Document IAM permissions needed for deployment
  - Document post-deployment verification steps
  - _Requirements: 7.5_

- [ ] 11. Checkpoint - Validate CloudFormation template
  - Run CloudFormation template validation (aws cloudformation validate-template)
  - Check for syntax errors and resource dependencies
  - Ensure all parameters are properly referenced
  - Ask the user if questions arise

## Notes

- This is an infrastructure-as-code project using AWS CloudFormation (YAML format)
- Lambda function code will be inline or referenced from S3
- All resources follow AWS security best practices with encryption and least-privilege IAM
- The pipeline is fully serverless and event-driven
- Cost optimization is built in through lifecycle policies and on-demand billing
- Monitoring and error handling are comprehensive with CloudWatch and SNS
