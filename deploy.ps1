# Market Analysis Pipeline Deployment Script
# This script packages Lambda functions and provides deployment instructions

param(
    [Parameter(Mandatory=$false)]
    [string]$StackName = "market-analysis-pipeline",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [string]$AlertEmail = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Market Analysis Pipeline Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is installed
try {
    $awsVersion = aws --version 2>&1
    Write-Host "AWS CLI found: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "AWS CLI not found. Please install AWS CLI first." -ForegroundColor Red
    exit 1
}

# Create deployment package directory
$deployDir = "deployment-package"
if (Test-Path $deployDir) {
    Remove-Item -Recurse -Force $deployDir
}
New-Item -ItemType Directory -Path $deployDir | Out-Null
Write-Host "Created deployment directory" -ForegroundColor Green

# Package Lambda functions
Write-Host ""
Write-Host "Packaging Lambda functions..." -ForegroundColor Yellow

# Copy Lambda files
Copy-Item "orchestrator_lambda.py" "$deployDir/orchestrator_lambda.py"
Copy-Item "parser_lambda.py" "$deployDir/parser_lambda.py"
Write-Host "Lambda functions copied" -ForegroundColor Green

# Create deployment instructions
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IMPORTANT: Template Size Issue" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The template.yaml file is too large for direct deployment." -ForegroundColor Yellow
Write-Host "You have two options:" -ForegroundColor Yellow
Write-Host ""

Write-Host "Option 1: Use AWS SAM (Recommended)" -ForegroundColor Cyan
Write-Host "  1. Install AWS SAM CLI" -ForegroundColor White
Write-Host "  2. Run: sam build" -ForegroundColor White
Write-Host "  3. Run: sam deploy --guided" -ForegroundColor White
Write-Host ""

Write-Host "Option 2: Upload Lambda code to S3" -ForegroundColor Cyan
Write-Host "  1. Create an S3 bucket for Lambda code" -ForegroundColor White
Write-Host "  2. Zip and upload Lambda functions" -ForegroundColor White
Write-Host "  3. Modify template.yaml to reference S3 locations" -ForegroundColor White
Write-Host ""

# Provide deployment commands
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Manual Deployment Steps (Option 2)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Create S3 bucket for Lambda code" -ForegroundColor Yellow
Write-Host "aws s3 mb s3://your-lambda-code-bucket-$Region" -ForegroundColor White
Write-Host ""

Write-Host "Step 2: Package Lambda functions" -ForegroundColor Yellow
Write-Host "cd deployment-package" -ForegroundColor White
Write-Host 'Compress-Archive -Path orchestrator_lambda.py -DestinationPath orchestrator.zip' -ForegroundColor White
Write-Host 'Compress-Archive -Path parser_lambda.py -DestinationPath parser.zip' -ForegroundColor White
Write-Host ""

Write-Host "Step 3: Upload to S3" -ForegroundColor Yellow
Write-Host "aws s3 cp orchestrator.zip s3://your-lambda-code-bucket/lambda/" -ForegroundColor White
Write-Host "aws s3 cp parser.zip s3://your-lambda-code-bucket/lambda/" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment package ready!" -ForegroundColor Green
Write-Host "Location: $deployDir" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
