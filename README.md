# Market Intelligence Analysis Pipeline

An automated, serverless AWS pipeline for processing and analyzing market intelligence documents. The system extracts text from documents, performs AI-powered analysis to identify competitors, financial metrics, strategic initiatives, and risks, then stores structured insights in a queryable database with a real-time dashboard for visualization.

## Overview

This project provides an end-to-end solution for market intelligence automation:

- **Automated Processing**: Upload documents to S3 and trigger automatic analysis
- **AI-Powered Analysis**: Uses AWS Bedrock (Claude 3 Haiku) to extract market insights
- **Structured Storage**: Stores insights in DynamoDB with multiple query indexes
- **Real-Time Dashboard**: Streamlit-based web interface with WebSocket push updates
- **Infrastructure as Code**: Complete CloudFormation templates for reproducible deployments

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│   S3 Bucket │─────▶│ Orchestrator     │─────▶│ AWS Textract│
│  (Upload)   │      │ Lambda           │      │ (PDF/Image) │
└─────────────┘      └──────────────────┘      └─────────────┘
                              │                        │
                              ▼                        │
                     ┌─────────────────┐              │
                     │  AWS Bedrock    │◀─────────────┘
                     │ (Claude Haiku)  │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Parser Lambda  │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐  Stream   ┌──────────────┐
                     │   DynamoDB      │──────────▶│  Notifier    │
                     │   (Insights)    │           │  Lambda      │
                     └────────┬────────┘           └──────┬───────┘
                              │                           │
                         reads data               push "reload"
                              │                    via WebSocket
                              ▼                           │
                     ┌──────────────────────────────────┐ │
                     │  Streamlit Dashboard (EC2)       │◀┘
                     │  CloudFront (HTTPS)              │
                     └──────────────────────────────────┘
```

### Components

1. **S3 Bucket**: Entry point for document uploads with event notifications
2. **Orchestrator Lambda**: Coordinates workflow — Textract for PDFs/images, direct read for text files, Bedrock for analysis
3. **AWS Textract**: Extracts text from PDF and image documents (sync for small, async for large)
4. **AWS Bedrock**: AI-powered analysis using Claude 3 Haiku (temperature 0.0 for strict extraction)
5. **Parser Lambda**: Validates, transforms, and stores analysis results
6. **DynamoDB Table**: Stores structured insights with GSI indexes and DynamoDB Streams enabled
7. **WebSocket API Gateway**: Pushes real-time notifications to dashboard on insert/modify/delete
8. **Streamlit Dashboard**: Web-based UI on EC2 behind CloudFront with file upload support

## Features

### Document Processing
- Accepts any file format — text files read directly, PDFs/images via Textract
- Textract fallback: sync API for small files, async for large, raw read if both fail
- Handles documents up to 10MB
- Upload via S3 CLI or directly from the dashboard sidebar

### AI Analysis
- Uses Claude 3 Haiku for fast structured extraction (~5-8s per document)
- Temperature 0.0 — only extracts data explicitly stated in the document
- Identifies competitors and market players
- Extracts key dates (launches, announcements, events)
- Captures financial metrics (revenue, funding, pricing)
- Identifies strategic initiatives and partnerships
- Detects market risks and opportunities

### Data Storage
- Structured insights stored in DynamoDB
- Multiple indexes for efficient querying:
  - DocumentId + Upload Timestamp
  - Party Name + Upload Timestamp
  - Effective Date + Upload Timestamp
- Point-in-time recovery for production environments

### Dashboard Features
- Dark theme with real-time WebSocket push updates
- File upload directly from the sidebar
- Competitor intelligence tracking with mention counts
- Financial metrics analysis
- Risk/Opportunity type distribution and analysis
- Document explorer with detailed views
- Searchable document filter with select all toggle
- Deployed on EC2 behind CloudFront (HTTPS)

### Real-Time Updates
- DynamoDB Streams triggers a notifier Lambda on insert/modify/delete
- WebSocket API Gateway pushes notifications to connected dashboard clients
- Dashboard auto-reloads when new data arrives — no manual refresh needed

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Python 3.9 or higher
- PowerShell (for deployment scripts)
- Streamlit 1.37+ (for dashboard with fragment support)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd market-intelligence-pipeline
```

### 2. Configure AWS Credentials

```bash
aws configure
```

### 3. Deploy Infrastructure

#### Option A: Using AWS SAM (Recommended)

```bash
# Install AWS SAM CLI
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html

# Build and deploy
sam build
sam deploy --guided
```

#### Option B: Manual Deployment

```powershell
# Run deployment script
.\deploy.ps1 -StackName "market-analysis-pipeline" -Environment "dev" -Region "us-east-1"
```

Follow the instructions provided by the script to:
1. Create S3 bucket for Lambda code
2. Package Lambda functions
3. Upload to S3
4. Deploy CloudFormation stack

### 4. Deploy Dashboard (Optional)

#### Option A: Local Development

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

#### Option B: EC2 Deployment

```powershell
# Deploy dashboard to EC2
.\deploy-dashboard.ps1
```

## Usage

### Upload Documents for Analysis

```bash
# Upload a document to S3
aws s3 cp sample_docs/competitor_report_q1_2024.txt s3://your-bucket-name/

# The pipeline will automatically:
# 1. Extract text using Textract
# 2. Analyze with Bedrock AI
# 3. Store insights in DynamoDB
```

### Access the Dashboard

1. Start the dashboard locally:
   ```bash
   cd dashboard
   streamlit run app.py
   ```

2. Open browser to `http://localhost:8501`

3. Use filters to explore:
   - Time periods (Last 7/30/90 days, All time)
   - Specific competitors
   - Document types

### Query Insights Programmatically

```python
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('market-analysis-market-insights-dev')

# Query by document ID
response = table.query(
    IndexName='DocumentIdIndex',
    KeyConditionExpression='documentId = :doc_id',
    ExpressionAttributeValues={':doc_id': 'competitor_report_q1_2024'}
)

# Query by competitor
response = table.query(
    IndexName='PartyNameIndex',
    KeyConditionExpression='partyName = :party',
    ExpressionAttributeValues={':party': 'Acme Corp'}
)
```

## Configuration

### CloudFormation Parameters

Key parameters you can customize during deployment:

- `ProjectName`: Project identifier (default: market-analysis)
- `Environment`: Deployment environment (dev/test/prod)
- `MarketBucketName`: S3 bucket name for documents
- `DynamoDBTableName`: DynamoDB table name (default: market-insights)
- `LambdaCodeBucket`: S3 bucket containing Lambda deployment packages
- `OrchestratorMemorySize`: Memory for orchestrator Lambda (default: 512MB)
- `ParserMemorySize`: Memory for parser Lambda (default: 256MB)
- `AlertEmail`: Email for critical error notifications

### Environment Variables

**Orchestrator Lambda**:
- `PARSER_LAMBDA_ARN`: ARN of the parser Lambda function
- `SNS_TOPIC_ARN`: ARN of the SNS topic for error notifications
- `ENVIRONMENT`: Deployment environment

**Parser Lambda**:
- `DYNAMODB_TABLE_NAME`: Name of the DynamoDB table
- `ENVIRONMENT`: Deployment environment

## Project Structure

```
.
├── IAC/
│   ├── template.yaml                # Main CloudFormation template (Lambda pipeline)
│   ├── dashboard-infrastructure.yaml # Dashboard EC2/CloudFront infrastructure
│   └── websocket-infrastructure.yaml # WebSocket API Gateway + notifier Lambda
├── deployment-package/
│   ├── orchestrator_lambda.py       # Orchestration Lambda (Textract + Bedrock)
│   └── parser_lambda.py             # Parser Lambda (DynamoDB writer)
├── dashboard/
│   ├── .streamlit/
│   │   └── config.toml              # Streamlit dark theme configuration
│   ├── app.py                       # Streamlit dashboard application
│   ├── requirements.txt             # Python dependencies (streamlit>=1.37)
│   └── README.md                    # Dashboard documentation
├── sample_docs/                     # Sample market intelligence documents (19 files)
│   ├── *.txt                        # 14 text-based competitive intelligence reports
│   ├── *.pdf                        # 5 PDF reports (generated with reportlab)
│   └── README.md
├── Tasks/specs/                     # Project specifications
│   └── Market-analysis-pipeline/
│       ├── requirements.md
│       ├── design.md
│       └── tasks.md
├── deploy.ps1                       # Main pipeline deployment script
├── deploy-dashboard.ps1             # Dashboard EC2 infrastructure deployment
├── copy-app-to-ec2.ps1             # Copy dashboard app + config to EC2 via SSM
├── .gitignore
└── README.md
```

## Security

The pipeline implements multiple security layers:

- **Encryption at Rest**: S3 and DynamoDB use AWS KMS encryption
- **Encryption in Transit**: All data transfers use TLS 1.2+
- **Least Privilege IAM**: Lambda functions have minimal required permissions
- **Public Access Blocking**: S3 bucket blocks all public access
- **Audit Logging**: CloudTrail logs all data access events
- **Key Rotation**: KMS keys have automatic rotation enabled

## Monitoring

### CloudWatch Metrics

The pipeline emits custom metrics:
- `JobSuccessRate`: Success/failure rate of analysis jobs
- `ProcessingDuration`: Time taken to process each document
- `ErrorCount`: Count of errors by type

### CloudWatch Logs

All Lambda functions log to CloudWatch Logs:
- `/aws/lambda/market-analysis-orchestrator-lambda-{env}`
- `/aws/lambda/market-analysis-parser-lambda-{env}`

### SNS Notifications

Critical errors trigger SNS notifications to the configured email address.

## Cost Optimization

- **On-Demand Billing**: DynamoDB uses pay-per-request pricing
- **Lifecycle Policies**: S3 archives processed documents to Glacier after 90 days
- **Async Processing**: Large documents use async Textract to avoid Lambda timeouts
- **Right-Sized Resources**: Lambda memory configured for optimal cost/performance

## Testing

### Sample Documents

The `sample_docs/` directory contains 19 market intelligence documents (14 TXT + 5 PDF) covering:
- Cloud infrastructure, cybersecurity, AI infrastructure, e-commerce platforms
- DevOps toolchains, healthcare SaaS, FinTech payments, data analytics
- Edge computing/IoT, HR tech, green tech/sustainability
- Digital advertising, semiconductor industry, enterprise AI adoption
- Supply chain technology, SaaS market analysis, startup funding, competitor reports

### Upload Test Documents

```bash
# Upload all sample documents
aws s3 cp sample_docs/ s3://your-bucket-name/ --recursive --exclude "README.md"
```

### Verify Processing

```bash
# Check Lambda logs
aws logs tail /aws/lambda/market-analysis-orchestrator-lambda-dev --follow

# Query DynamoDB
aws dynamodb scan --table-name market-analysis-market-insights-dev
```

## Troubleshooting

### Lambda Function Errors

Check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/market-analysis-orchestrator-lambda-dev --follow
```

### Bedrock Analysis Issues

- Ensure Bedrock model access is enabled in your AWS account
- Check IAM permissions for `bedrock:InvokeModel`
- Verify the model ID is correct for your region

### DynamoDB Write Failures

- Check IAM permissions for `dynamodb:PutItem`
- Verify table name matches environment configuration
- Check KMS key permissions for encryption

### Dashboard Connection Issues

Update the table name in `dashboard/app.py`:
```python
table = dynamodb.Table('your-table-name-here')
```

## Development

### Local Testing

Test Lambda functions locally:

```python
# Test orchestrator
python -c "from deployment_package.orchestrator_lambda import lambda_handler; print(lambda_handler(test_event, None))"

# Test parser
python -c "from deployment_package.parser_lambda import lambda_handler; print(lambda_handler(test_event, None))"
```

### Running Dashboard Locally

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Specify your license here]

## Support

For issues and questions:
- Check CloudWatch Logs for error details
- Review the specification documents in `Tasks/specs/contract-analysis-pipeline/`
- Consult AWS documentation for service-specific issues

## Roadmap

Future enhancements:
- Support for additional document formats
- Multi-language document analysis
- Advanced sentiment analysis
- Automated competitive intelligence reports
- Integration with business intelligence tools
- Real-time alerting for critical market events
