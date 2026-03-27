# Market Intelligence Dashboard

Professional Streamlit dashboard for visualizing market intelligence insights from DynamoDB.

## Features

### 📊 Overview Dashboard
- Real-time metrics (documents, competitors, risks, initiatives)
- Timeline visualization of document processing
- Top competitors by mentions
- Recent insights feed

### 🏢 Competitor Intelligence
- Competitor profiles with market positions
- Strategic initiatives tracking
- Document mentions and analysis
- Role-based categorization

### 💰 Financial Intelligence
- Funding rounds and valuations
- Revenue metrics
- Pricing analysis
- Financial trends visualization

### ⚠️ Risk Analysis
- Risk type distribution
- Opportunity identification
- Threat assessment
- Risk categorization with pie charts

### 📋 Document Explorer
- Detailed document view
- Metadata inspection
- Structured data tables
- Raw JSON viewer

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials:
```bash
aws configure
```

## Usage

Run the dashboard:
```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Features

### Filters
- Date range selection (Last 7/30/90 days, All time)
- Competitor multi-select
- Document type filtering

### Visualizations
- Interactive Plotly charts
- Timeline graphs
- Pie charts for distributions
- Bar charts for comparisons
- Data tables with sorting/filtering

### Data Refresh
- Auto-refresh every 5 minutes
- Manual refresh with sidebar button
- Real-time data from DynamoDB

## Dashboard Sections

### 1. Key Metrics (Top Row)
- Total Documents Processed
- Competitors Tracked
- Risk Factors Identified
- Strategic Initiatives

### 2. Overview Tab
- Documents processed timeline
- Top 10 competitors by mentions
- Recent insights cards

### 3. Competitors Tab
- Expandable competitor cards
- Market position and roles
- Strategic initiatives list
- Document references

### 4. Financial Intelligence Tab
- Financial metrics table
- Funding analysis
- Revenue tracking
- Valuation trends

### 5. Risk Analysis Tab
- Risk type pie chart
- Detailed risk table
- Competitor-specific risks
- Opportunity identification

### 6. Document Explorer Tab
- Document selector dropdown
- Metadata display
- Tabbed analysis results
- Raw JSON viewer

## Customization

### Styling
Edit the CSS in `app.py` to customize:
- Colors and gradients
- Card styles
- Typography
- Layout spacing

### Data Source
Update the DynamoDB table name in `init_aws_clients()`:
```python
table = dynamodb.Table('your-table-name')
```

### Metrics
Add custom metrics in the `show_overview()` function

### Charts
Customize Plotly charts with different:
- Chart types (line, bar, pie, scatter)
- Color schemes
- Layouts and themes

## AWS Configuration

Ensure your AWS credentials have permissions for:
- `dynamodb:Scan`
- `dynamodb:Query`
- `dynamodb:GetItem`

## Performance

- Data is cached for 5 minutes using `@st.cache_data`
- AWS clients are cached using `@st.cache_resource`
- Pagination handled automatically for large datasets

## Troubleshooting

### No data showing
- Check AWS credentials: `aws sts get-caller-identity`
- Verify DynamoDB table name
- Ensure table has data: `aws dynamodb scan --table-name market-analysis-market-insights-dev --limit 1`

### Slow loading
- Reduce cache TTL in `@st.cache_data(ttl=300)`
- Limit data with filters
- Use DynamoDB queries instead of scans

### Chart errors
- Check data format in DynamoDB
- Verify Decimal conversion in `decimal_to_float()`
- Ensure required fields exist

## Future Enhancements

- [ ] Export to PDF/Excel
- [ ] Email alerts for new insights
- [ ] Sentiment analysis visualization
- [ ] Competitive positioning matrix
- [ ] Trend prediction with ML
- [ ] Custom report builder
- [ ] Multi-user authentication
- [ ] Real-time WebSocket updates
