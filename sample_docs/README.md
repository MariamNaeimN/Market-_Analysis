# Sample Market Intelligence Documents

This directory contains sample market intelligence documents for testing the market analysis pipeline.

## Document Categories

### 1. Competitor Intelligence Reports
- `competitor_report_q1_2024.txt` - Quarterly competitive analysis of cloud services market
  - Competitor movements and strategic initiatives
  - Funding rounds and valuations
  - Market trends and opportunities
  - Risk assessment

### 2. Funding & Investment News
- `tech_startup_funding_news.txt` - Weekly digest of major funding rounds
  - DataStream AI: $850M Series E
  - CloudNative Systems: $320M Series D
  - SecureChain Technologies: $180M Series C
  - Emerging competitors and market analysis
  - Sector trends and valuation metrics

### 3. Market Analysis Reports
- `saas_market_analysis_2024.txt` - Comprehensive SaaS market landscape
  - Market leaders: Salesforce, ServiceNow, Workday
  - Emerging disruptors: Notion, Retool, Rippling
  - Pricing analysis and benchmarks
  - Technology trends and competitive dynamics
  - Strategic recommendations

### 4. Legacy Contract Documents (for reference)
- `software_license_agreement.txt` - Software licensing agreement
- `master_service_agreement.txt` - MSA between service providers
- `employment_agreement.txt` - Executive employment contract

## Document Structure

All market intelligence documents include:
- **Parties/Competitors**: Company names and market positions
- **Dates**: Key dates for events, announcements, launches
- **Financial Information**: Revenue, funding, pricing, valuations
- **Strategic Initiatives**: Partnerships, acquisitions, expansions
- **Risks & Opportunities**: Market threats and growth opportunities

## Usage

Upload these files to the S3 bucket to trigger the market intelligence analysis pipeline:

```bash
# Upload competitor report
aws s3 cp competitor_report_q1_2024.txt s3://market-analysis-markets-dev-193786182229/

# Upload funding news
aws s3 cp tech_startup_funding_news.txt s3://market-analysis-markets-dev-193786182229/

# Upload market analysis
aws s3 cp saas_market_analysis_2024.txt s3://market-analysis-markets-dev-193786182229/
```

## Pipeline Flow

The pipeline will:
1. **Extract text** - Textract for PDFs, direct read for TXT files
2. **Analyze with Bedrock AI** - Extract structured market intelligence
3. **Parse and validate** - Validate JSON structure and field types
4. **Store in DynamoDB** - Save structured insights with metadata

## Expected Output Schema

```json
{
  "parties": [
    {"name": "Company Name", "role": "Market Position"}
  ],
  "dates": {
    "effectiveDate": "YYYY-MM-DD",
    "terminationDate": "YYYY-MM-DD or null"
  },
  "paymentTerms": [
    {"description": "Financial metric", "amount": "Amount"}
  ],
  "obligations": [
    {"party": "Company", "obligation": "Strategic initiative"}
  ],
  "risks": [
    {"type": "Risk type", "description": "Description"}
  ]
}
```

## Document Formats

- **TXT**: ASCII art formatted for readability
- **PDF**: (Future) Formatted documents with tables and charts

## Testing

To test the full pipeline:

1. Upload a document to S3
2. Check Orchestrator Lambda logs: `/aws/lambda/market-analysis-orchestrator-lambda-dev`
3. Check Parser Lambda logs: `/aws/lambda/market-analysis-parser-lambda-dev`
4. Query DynamoDB table: `market-analysis-market-insights-dev`

```bash
# View logs
aws logs tail /aws/lambda/market-analysis-orchestrator-lambda-dev --follow

# Query DynamoDB
aws dynamodb scan --table-name market-analysis-market-insights-dev --limit 5
```

## Market Intelligence Focus

These documents are designed to extract:
- Competitor strategies and positioning
- Funding rounds and valuations
- Product launches and pricing
- Market trends and opportunities
- Strategic partnerships and M&A activity
- Financial performance metrics
- Risk factors and threats
