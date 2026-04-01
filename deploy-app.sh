cd /opt/dashboard
aws s3 cp s3://your-lambda-code-bucket-us-east-1/dashboard-app/app.py app.py
chown ec2-user:ec2-user app.py
chmod 644 app.py
sudo systemctl restart streamlit-dashboard
sleep 3
sudo systemctl status streamlit-dashboard --no-pager
