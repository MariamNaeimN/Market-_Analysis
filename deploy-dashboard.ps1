# Deploy Market Intelligence Dashboard Infrastructure
# This script deploys the Streamlit dashboard on EC2 with CloudFront

param(
    [string]$Environment = "dev",
    [string]$KeyPairName = "",
    [string]$InstanceType = "t3.small"
)

$StackName = "market-intelligence-dashboard-$Environment"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying Market Intelligence Dashboard" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Instance Type: $InstanceType" -ForegroundColor Yellow
Write-Host "Stack Name: $StackName" -ForegroundColor Yellow
Write-Host ""

# Step 0: Upload app.py to S3
Write-Host "Step 0: Uploading app.py to S3..." -ForegroundColor Green
$S3Bucket = "your-lambda-code-bucket-us-east-1"
$S3Key = "dashboard-app/app.py"

if (Test-Path "dashboard/app.py") {
    aws s3 cp dashboard/app.py "s3://$S3Bucket/$S3Key"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "app.py uploaded to S3 successfully" -ForegroundColor Green
    } else {
        Write-Host "Warning: Failed to upload app.py to S3" -ForegroundColor Yellow
    }
} else {
    Write-Host "Warning: dashboard/app.py not found, skipping upload" -ForegroundColor Yellow
}
Write-Host ""

# Deploy CloudFormation stack
Write-Host "Step 1: Deploying CloudFormation stack..." -ForegroundColor Green

$params = @(
    "ParameterKey=Environment,ParameterValue=$Environment",
    "ParameterKey=InstanceType,ParameterValue=$InstanceType"
)

if ($KeyPairName) {
    $params += "ParameterKey=KeyPairName,ParameterValue=$KeyPairName"
}

aws cloudformation create-stack `
    --stack-name $StackName `
    --template-body file://IAC/dashboard-infrastructure.yaml `
    --parameters $params `
    --capabilities CAPABILITY_NAMED_IAM `
    --tags Key=Environment,Value=$Environment Key=Project,Value=market-intelligence

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create stack. Checking if update is needed..." -ForegroundColor Yellow
    
    aws cloudformation update-stack `
        --stack-name $StackName `
        --template-body file://IAC/dashboard-infrastructure.yaml `
        --parameters $params `
        --capabilities CAPABILITY_NAMED_IAM
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Stack update failed or no changes detected" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Step 2: Waiting for stack creation to complete..." -ForegroundColor Green
Write-Host "This may take 5-10 minutes..." -ForegroundColor Yellow

aws cloudformation wait stack-create-complete --stack-name $StackName

if ($LASTEXITCODE -ne 0) {
    Write-Host "Stack creation failed!" -ForegroundColor Red
    aws cloudformation describe-stack-events --stack-name $StackName --max-items 10
    exit 1
}

Write-Host ""
Write-Host "Step 3: Retrieving stack outputs..." -ForegroundColor Green

$outputs = aws cloudformation describe-stacks --stack-name $StackName --query 'Stacks[0].Outputs' | ConvertFrom-Json

$ec2PublicDNS = ($outputs | Where-Object { $_.OutputKey -eq "EC2PublicDNS" }).OutputValue
$cloudFrontURL = ($outputs | Where-Object { $_.OutputKey -eq "CloudFrontURL" }).OutputValue
$ec2InstanceId = ($outputs | Where-Object { $_.OutputKey -eq "EC2InstanceId" }).OutputValue

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stack Created Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "EC2 Instance ID: $ec2InstanceId" -ForegroundColor Yellow
Write-Host "EC2 Public DNS: $ec2PublicDNS" -ForegroundColor Yellow
Write-Host ""
Write-Host "Direct Access (HTTP): http://${ec2PublicDNS}:8501" -ForegroundColor Yellow
Write-Host "CloudFront Access (HTTPS): $cloudFrontURL" -ForegroundColor Yellow
Write-Host ""

Write-Host "Step 4: Deploying dashboard application..." -ForegroundColor Green
Write-Host ""

# Wait for instance to be ready
Write-Host "Waiting for EC2 instance to be ready..." -ForegroundColor Yellow
aws ec2 wait instance-status-ok --instance-ids $ec2InstanceId

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Copy dashboard files to EC2:" -ForegroundColor White
Write-Host "   scp -i your-key.pem dashboard/app.py ec2-user@${ec2PublicDNS}:/opt/dashboard/" -ForegroundColor Gray
Write-Host ""
Write-Host "2. SSH to EC2 and restart service:" -ForegroundColor White
Write-Host "   ssh -i your-key.pem ec2-user@$ec2PublicDNS" -ForegroundColor Gray
Write-Host "   sudo systemctl restart streamlit-dashboard" -ForegroundColor Gray
Write-Host "   sudo systemctl status streamlit-dashboard" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Access dashboard:" -ForegroundColor White
Write-Host "   CloudFront (HTTPS): $cloudFrontURL" -ForegroundColor Gray
Write-Host "   Direct (HTTP): http://${ec2PublicDNS}:8501" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
