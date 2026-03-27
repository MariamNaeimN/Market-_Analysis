#!/usr/bin/env pwsh
# Script to copy dashboard app to EC2 instance using S3 as intermediary

param(
    [string]$Environment = "dev"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying Dashboard App to EC2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$StackName = "market-intelligence-dashboard-$Environment"

# Check if app.py exists
if (-not (Test-Path "dashboard/app.py")) {
    Write-Host "Error: dashboard/app.py not found!" -ForegroundColor Red
    exit 1
}

# Get instance ID
Write-Host "Step 1: Getting EC2 instance details..." -ForegroundColor Yellow
$InstanceId = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query 'Stacks[0].Outputs[?OutputKey==`EC2InstanceId`].OutputValue' `
    --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to get instance ID" -ForegroundColor Red
    exit 1
}

Write-Host "Instance ID: $InstanceId" -ForegroundColor Green
Write-Host ""

# Upload app.py to S3 temporarily
Write-Host "Step 2: Uploading app.py to S3..." -ForegroundColor Yellow
$S3Bucket = "your-lambda-code-bucket-us-east-1"
$S3Key = "dashboard-app/app.py"

aws s3 cp dashboard/app.py "s3://$S3Bucket/$S3Key"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to upload to S3" -ForegroundColor Red
    exit 1
}

Write-Host "Uploaded to s3://$S3Bucket/$S3Key" -ForegroundColor Green
Write-Host ""

# Download from S3 to EC2 and restart service
Write-Host "Step 3: Deploying to EC2 via SSM..." -ForegroundColor Yellow

$DeployScript = @"
#!/bin/bash
set -e
cd /opt/dashboard
aws s3 cp s3://$S3Bucket/$S3Key app.py
chown ec2-user:ec2-user app.py
chmod 644 app.py
sudo systemctl restart streamlit-dashboard
sleep 3
sudo systemctl status streamlit-dashboard --no-pager
"@

# Execute via SSM
$CommandId = aws ssm send-command `
    --instance-ids $InstanceId `
    --document-name "AWS-RunShellScript" `
    --parameters "commands=['$DeployScript']" `
    --query 'Command.CommandId' `
    --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to send SSM command" -ForegroundColor Red
    exit 1
}

Write-Host "Command ID: $CommandId" -ForegroundColor Green
Write-Host "Waiting for deployment to complete..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Get command output
$Output = aws ssm get-command-invocation `
    --command-id $CommandId `
    --instance-id $InstanceId `
    --query '[Status,StandardOutputContent,StandardErrorContent]' `
    --output json | ConvertFrom-Json

Write-Host ""
Write-Host "Deployment Status: $($Output[0])" -ForegroundColor $(if ($Output[0] -eq "Success") { "Green" } else { "Red" })

if ($Output[1]) {
    Write-Host ""
    Write-Host "Output:" -ForegroundColor Cyan
    Write-Host $Output[1]
}

if ($Output[2]) {
    Write-Host ""
    Write-Host "Errors:" -ForegroundColor Yellow
    Write-Host $Output[2]
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Get URLs
$CloudFrontURL = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' `
    --output text

$DirectURL = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query 'Stacks[0].Outputs[?OutputKey==`DashboardDirectURL`].OutputValue' `
    --output text

Write-Host "Access your dashboard at:" -ForegroundColor Cyan
Write-Host "  Direct EC2 (HTTP):  $DirectURL" -ForegroundColor White
Write-Host "  CloudFront (HTTPS): $CloudFrontURL" -ForegroundColor White
Write-Host ""
Write-Host "Note: Try the Direct URL first. CloudFront may take 5-10 minutes to start working." -ForegroundColor Yellow
Write-Host ""

# Clean up S3
Write-Host "Cleaning up S3..." -ForegroundColor Yellow
aws s3 rm "s3://$S3Bucket/$S3Key" --quiet
