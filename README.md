# Market Intelligence Analysis Pipeline

An automated, serverless AWS pipeline for processing and analyzing market intelligence documents. The system extracts text from documents, performs AI-powered analysis to identify competitors, financial metrics, strategic initiatives, and risks, then stores structured insights in a queryable database with a real-time dashboard for visualization.

## Overview

This project provides an end-to-end solution for market intelligence automation:

- **Automated Processing**: Upload documents to S3 and trigger automatic analysis
- **AI-Powered Analysis**: Uses AWS Bedrock (Claude Sonnet 4) to extract market insights
- **Structured Storage**: Stores insights in DynamoDB with multiple query indexes
- **Real-Time Dashboard**: Streamlit-based web interface for exploring insights
- **Infrastructure as Code**: Complete CloudFormation templates for reproducible deployments

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│   S3 Bucket │─────▶│ Orchestrator     │─────▶│ AWS Textract│
│  (Upload)   │      │ Lambda           │      │             │
└─────────────┘      └──────────────────┘      └─────────────┘
                              │                        │
                              ▼                        │
                     ┌─────────────────┐              │
                     │  AWS Bedrock    │◀─────────────┘
                     │  (Claude 3.5)   │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Parser Lambda  │
                     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐      ┌──────────────┐
                     │   DynamoDB      │◀─────│  Dashboard   │
                     │   (Insights)    │      │  (Streamlit) │
                     └─────────────────┘      └──────────────┘
```

### Components

1. **S3 Bucket**: Entry point for document uploads with event notifications
2. **Orchestrator Lambda**: Coordinates workflow, manages Textract and Bedrock interactions
3. **AWS Textract**: Extracts text from PDF and image documents
4. **AWS Bedrock**: AI-powered analysis using Claude 3.5 Sonnet model
5. **Parser Lambda**: Validates, transforms, and stores analysis results
6. **DynamoDB Table**: Stores structured insights with GSI indexes for querying
7. **Streamlit Dashboard**: Web-based UI for exploring and visualizing insights

## Features

### Document Processing
- Supports PDF, PNG, JPEG, TIFF, and TXT formats
- Automatic text extraction using AWS Textract
- Handles documents up to 10MB
- Asynchronous processing for large files (>1MB)

### AI Analysis
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
- Real-time data visualization
- Competitor intelligence tracking
- Financial metrics analysis
- Risk and opportunity assessment
- Document explorer with detailed views
- Interactive filters and date range selection

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Python 3.11 or higher
- PowerShell (for deployment scripts)
- Streamlit (for dashboard)

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
│   └── dashboard-infrastructure.yaml # Dashboard EC2/CloudFront infrastructure
├── deployment-package/
│   ├── orchestrator_lambda.py       # Orchestration Lambda function
│   └── parser_lambda.py             # Parser Lambda function
├── dashboard/
│   ├── .streamlit/
│   │   └── config.toml              # Streamlit dark theme configuration
│   ├── app.py                       # Streamlit dashboard application
│   ├── requirements.txt             # Python dependencies
│   └── README.md                    # Dashboard documentation
├── sample_docs/                     # Sample market intelligence documents
│   ├── ai_infrastructure_competitive_report.txt
│   ├── competitive_intelligence_facebook.txt
│   ├── competitor_report_q1_2024.txt
│   ├── cybersecurity_market_q2_2024.txt
│   ├── data_analytics_platforms_2024.txt
│   ├── devops_toolchain_market_2024.txt
│   ├── ecommerce_platform_analysis_2024.txt
│   ├── edge_computing_iot_market_2024.txt
│   ├── fintech_payments_landscape_2024.txt
│   ├── green_tech_sustainability_market_2024.txt
│   ├── healthcare_saas_competitive_2024.txt
│   ├── hr_tech_workforce_platforms_2024.txt
│   ├── saas_market_analysis_2024.txt
│   ├── tech_startup_funding_news.txt
│   └── README.md
├── Tasks/specs/                     # Project specifications
│   └── contract-analysis-pipeline/
│       ├── .config.kiro
│       ├── requirements.md
│       ├── design.md
│       └── tasks.md
├── deploy.ps1                       # Main pipeline deployment script
├── deploy-dashboard.ps1             # Dashboard EC2 deployment script
├── copy-app-to-ec2.ps1             # Copy dashboard app to EC2 via SSM
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

The `sample_docs/` directory contains 14 market intelligence documents covering:
- `competitor_report_q1_2024.txt`: Quarterly competitor analysis (cloud services)
- `saas_market_analysis_2024.txt`: SaaS market trends and competitive landscape
- `tech_startup_funding_news.txt`: Startup funding announcements
- `competitive_intelligence_facebook.txt`: Meta/Facebook competitive intelligence
- `cybersecurity_market_q2_2024.txt`: Cybersecurity market analysis
- `ai_infrastructure_competitive_report.txt`: AI infrastructure competitive report
- `ecommerce_platform_analysis_2024.txt`: E-commerce platform market
- `devops_toolchain_market_2024.txt`: DevOps toolchain market
- `healthcare_saas_competitive_2024.txt`: Healthcare SaaS market
- `fintech_payments_landscape_2024.txt`: FinTech payments landscape
- `data_analytics_platforms_2024.txt`: Data analytics platforms
- `edge_computing_iot_market_2024.txt`: Edge computing and IoT market
- `hr_tech_workforce_platforms_2024.txt`: HR tech and workforce platforms
- `green_tech_sustainability_market_2024.txt`: Green tech and sustainability

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

### Textract Failures

Common issues:
- Unsupported file format (use PDF, PNG, JPEG, TIFF, or TXT)
- File size exceeds 10MB limit
- Corrupted or password-protected documents

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
