#!/usr/bin/env pwsh
# Script to copy dashboard app to EC2 instance using S3 as intermediary

param(
    [string]$Environment = "dev"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploying Dashboard App to EC2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$StackName = "market-intelligence-dashboard-$Environment"

# Check if app.py exists
if (-not (Test-Path "dashboard/app.py")) {
    Write-Host "Error: dashboard/app.py not found!" -ForegroundColor Red
    exit 1
}

# Check if config.toml exists
$HasConfig = Test-Path "dashboard/.streamlit/config.toml"
$HasRequirements = Test-Path "dashboard/requirements.txt"

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
Write-Host "Step 2: Uploading files to S3..." -ForegroundColor Yellow
$S3Bucket = "your-lambda-code-bucket-us-east-1"
$S3Key = "dashboard-app/app.py"
$S3ConfigKey = "dashboard-app/config.toml"
$S3RequirementsKey = "dashboard-app/requirements.txt"

aws s3 cp dashboard/app.py "s3://$S3Bucket/$S3Key"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to upload app.py to S3" -ForegroundColor Red
    exit 1
}

if ($HasConfig) {
    aws s3 cp "dashboard/.streamlit/config.toml" "s3://$S3Bucket/$S3ConfigKey"
    Write-Host "Uploaded config.toml to S3" -ForegroundColor Green
}

if ($HasRequirements) {
    aws s3 cp "dashboard/requirements.txt" "s3://$S3Bucket/$S3RequirementsKey"
    Write-Host "Uploaded requirements.txt to S3" -ForegroundColor Green
}

Write-Host "Uploaded to s3://$S3Bucket/$S3Key" -ForegroundColor Green
Write-Host ""

# Download from S3 to EC2 and restart service
Write-Host "Step 3: Deploying to EC2 via SSM..." -ForegroundColor Yellow

$Commands = @(
    "cd /opt/dashboard",
    "aws s3 cp s3://$S3Bucket/$S3Key app.py",
    "mkdir -p .streamlit",
    "aws s3 cp s3://$S3Bucket/$S3ConfigKey .streamlit/config.toml || true",
    "aws s3 cp s3://$S3Bucket/$S3RequirementsKey requirements.txt || true",
    "python3.11 -m pip install -r requirements.txt 2>&1 || python3 -m pip install -r requirements.txt 2>&1",
    "chown -R ec2-user:ec2-user /opt/dashboard",
    "chmod 644 app.py",
    "sudo systemctl restart streamlit-dashboard",
    "sleep 3",
    "sudo systemctl status streamlit-dashboard --no-pager 2>&1 | cat"
)

$CommandsJson = ($Commands | ForEach-Object { "`"$_`"" }) -join ","

# Write parameters to temp file to avoid escaping issues
$ParamsJson = '{"commands":[' + $CommandsJson + ']}'
$TempParamsFile = [System.IO.Path]::GetTempFileName()
Set-Content -Path $TempParamsFile -Value $ParamsJson -NoNewline

# Execute via SSM
$CommandId = aws ssm send-command `
    --instance-ids $InstanceId `
    --document-name "AWS-RunShellScript" `
    --parameters "file://$TempParamsFile" `
    --query 'Command.CommandId' `
    --output text

Remove-Item $TempParamsFile -ErrorAction SilentlyContinue

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to send SSM command" -ForegroundColor Red
    exit 1
}

Write-Host "Command ID: $CommandId" -ForegroundColor Green
Write-Host "Waiting for deployment to complete..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Get command output
$Status = aws ssm get-command-invocation `
    --command-id $CommandId `
    --instance-id $InstanceId `
    --query 'Status' `
    --output text

$StdOut = aws ssm get-command-invocation `
    --command-id $CommandId `
    --instance-id $InstanceId `
    --query 'StandardOutputContent' `
    --output text

$StdErr = aws ssm get-command-invocation `
    --command-id $CommandId `
    --instance-id $InstanceId `
    --query 'StandardErrorContent' `
    --output text

Write-Host ""
Write-Host "Deployment Status: $Status" -ForegroundColor $(if ($Status -eq "Success") { "Green" } else { "Red" })

if ($StdOut) {
    Write-Host ""
    Write-Host "Output:" -ForegroundColor Cyan
    Write-Host $StdOut
}

if ($StdErr) {
    Write-Host ""
    Write-Host "Errors:" -ForegroundColor Yellow
    Write-Host $StdErr
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
aws s3 rm "s3://$S3Bucket/$S3ConfigKey" --quiet
aws s3 rm "s3://$S3Bucket/$S3RequirementsKey" --quiet
