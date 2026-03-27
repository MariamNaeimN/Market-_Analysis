import streamlit as st
import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from decimal import Decimal

# Page configuration
st.set_page_config(
    page_title="Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 0.5rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .insight-card {
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        margin-bottom: 0.75rem;
    }
    .insight-card h4 {
        color: #000000;
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }
    .insight-card p {
        color: #000000;
        font-size: 0.9rem;
        margin: 0.25rem 0;
        line-height: 1.4;
    }
    .insight-card strong {
        color: #000000;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize AWS clients
@st.cache_resource
def init_aws_clients():
    """Initialize AWS clients with caching"""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('market-analysis-market-insights-dev')
    return table

# Helper function to convert Decimal to float
def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

# Load data from DynamoDB
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_insights():
    """Load all insights from DynamoDB"""
    table = init_aws_clients()
    
    try:
        response = table.scan()
        items = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        return items
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return []

# Parse and structure data
def parse_insights(items):
    """Parse insights into structured format"""
    insights = []
    
    for item in items:
        try:
            # Convert Decimal to int for timestamp
            upload_ts = item.get('uploadTimestamp', 0)
            if isinstance(upload_ts, Decimal):
                upload_ts = int(upload_ts)
            
            insight = {
                'insightId': item.get('insightId', 'N/A'),
                'documentId': item.get('documentId', 'N/A'),
                'jobId': item.get('jobId', 'N/A'),
                'partyName': item.get('partyName', 'Unknown'),
                'effectiveDate': item.get('effectiveDate', 'Unknown'),
                'uploadTimestamp': upload_ts,
                'processingTimestamp': item.get('processingTimestamp', 'N/A'),
                'environment': item.get('environment', 'N/A'),
                's3Metadata': item.get('s3Metadata', {}),
                'analysisResults': item.get('analysisResults', {})
            }
            insights.append(insight)
        except Exception as e:
            st.warning(f"Error parsing insight: {str(e)}")
            continue
    
    return insights

# Main dashboard
def main():
    # Header
    st.markdown('<div class="main-header">📊 Market Intelligence Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time competitive intelligence and market insights</div>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner('Loading market intelligence data...'):
        items = load_insights()
        insights = parse_insights(items)
    
    if not insights:
        st.warning("No insights found. Upload documents to S3 to generate market intelligence.")
        return
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    date_options = ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]
    date_filter = st.sidebar.selectbox("Select period", date_options, index=1)
    
    # Competitor filter
    all_competitors = sorted(list(set([i['partyName'] for i in insights if i['partyName'] != 'Unknown'])))
    selected_competitors = st.sidebar.multiselect(
        "Select Competitors",
        options=all_competitors,
        default=all_competitors[:5] if len(all_competitors) > 5 else all_competitors
    )
    
    # Document type filter
    doc_types = sorted(list(set([i['documentId'] for i in insights])))
    selected_docs = st.sidebar.multiselect(
        "Document Types",
        options=doc_types,
        default=doc_types
    )
    
    # Apply filters
    filtered_insights = [
        i for i in insights 
        if i['partyName'] in selected_competitors 
        and i['documentId'] in selected_docs
    ]
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📄 Total Documents",
            value=len(filtered_insights),
            delta=f"{len(insights) - len(filtered_insights)} filtered out"
        )
    
    with col2:
        unique_competitors = len(set([i['partyName'] for i in filtered_insights]))
        st.metric(
            label="🏢 Competitors Tracked",
            value=unique_competitors
        )
    
    with col3:
        # Count total risks across all insights
        total_risks = sum([
            len(i['analysisResults'].get('risks', [])) 
            for i in filtered_insights
        ])
        st.metric(
            label="⚠️ Risk Factors",
            value=total_risks
        )
    
    with col4:
        # Count total strategic initiatives
        total_initiatives = sum([
            len(i['analysisResults'].get('obligations', [])) 
            for i in filtered_insights
        ])
        st.metric(
            label="🎯 Strategic Initiatives",
            value=total_initiatives
        )
    
    st.divider()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Overview", 
        "🏢 Competitors", 
        "💰 Financial Intelligence",
        "⚠️ Risk Analysis",
        "📋 Document Explorer"
    ])
    
    with tab1:
        show_overview(filtered_insights)
    
    with tab2:
        show_competitors(filtered_insights)
    
    with tab3:
        show_financial_intelligence(filtered_insights)
    
    with tab4:
        show_risk_analysis(filtered_insights)
    
    with tab5:
        show_document_explorer(filtered_insights)

def show_overview(insights):
    """Overview dashboard with key visualizations"""
    st.subheader("Market Intelligence Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Documents processed over time
        st.markdown("#### 📅 Documents Processed Timeline")
        
        df_timeline = pd.DataFrame([
            {
                'date': datetime.fromtimestamp(i['uploadTimestamp']),
                'document': i['documentId']
            }
            for i in insights
        ])
        
        if not df_timeline.empty:
            df_timeline['date'] = pd.to_datetime(df_timeline['date'])
            timeline_counts = df_timeline.groupby(df_timeline['date'].dt.date).size().reset_index()
            timeline_counts.columns = ['Date', 'Count']
            
            fig = px.line(
                timeline_counts, 
                x='Date', 
                y='Count',
                markers=True,
                title="Documents Processed Over Time"
            )
            fig.update_traces(line_color='#667eea', marker=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timeline data available")
    
    with col2:
        # Competitor distribution
        st.markdown("#### 🏢 Competitor Mentions")
        
        competitor_counts = {}
        for insight in insights:
            parties = insight['analysisResults'].get('parties', [])
            for party in parties:
                name = party.get('name', 'Unknown')
                competitor_counts[name] = competitor_counts.get(name, 0) + 1
        
        if competitor_counts:
            df_competitors = pd.DataFrame(
                list(competitor_counts.items()),
                columns=['Competitor', 'Mentions']
            ).sort_values('Mentions', ascending=False).head(10)
            
            fig = px.bar(
                df_competitors,
                x='Mentions',
                y='Competitor',
                orientation='h',
                title="Top 10 Competitors by Mentions"
            )
            fig.update_traces(marker_color='#764ba2')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No competitor data available")
    
    # Recent insights
    st.markdown("#### 🔔 Recent Insights")
    
    recent_insights = sorted(insights, key=lambda x: x['uploadTimestamp'], reverse=True)[:5]
    
    for insight in recent_insights:
        with st.container():
            st.markdown(f"""
            <div class="insight-card">
                <h4>📄 {insight['documentId']}</h4>
                <p><strong>Primary Competitor:</strong> {insight['partyName']}</p>
                <p><strong>Date:</strong> {insight['effectiveDate']}</p>
                <p><strong>Processed:</strong> {insight['processingTimestamp']}</p>
            </div>
            """, unsafe_allow_html=True)

def show_competitors(insights):
    """Competitor analysis view"""
    st.subheader("Competitor Intelligence")
    
    # Build competitor profiles
    competitor_profiles = {}
    
    for insight in insights:
        parties = insight['analysisResults'].get('parties', [])
        obligations = insight['analysisResults'].get('obligations', [])
        
        for party in parties:
            name = party.get('name', 'Unknown')
            role = party.get('role', 'N/A')
            
            if name not in competitor_profiles:
                competitor_profiles[name] = {
                    'name': name,
                    'roles': set(),
                    'mentions': 0,
                    'initiatives': [],
                    'documents': []
                }
            
            competitor_profiles[name]['roles'].add(role)
            competitor_profiles[name]['mentions'] += 1
            competitor_profiles[name]['documents'].append(insight['documentId'])
        
        # Add strategic initiatives
        for obligation in obligations:
            party_name = obligation.get('party', '')
            initiative = obligation.get('obligation', '')
            if party_name in competitor_profiles:
                competitor_profiles[party_name]['initiatives'].append(initiative)
    
    # Display competitor cards
    for name, profile in sorted(competitor_profiles.items(), key=lambda x: x[1]['mentions'], reverse=True):
        with st.expander(f"🏢 {name} ({profile['mentions']} mentions)", expanded=False):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Market Position:** {', '.join(profile['roles'])}")
                st.markdown(f"**Documents:** {', '.join(set(profile['documents']))}")
                
                if profile['initiatives']:
                    st.markdown("**Strategic Initiatives:**")
                    for initiative in profile['initiatives'][:5]:
                        st.markdown(f"- {initiative}")
            
            with col2:
                st.metric("Mention Count", profile['mentions'])

def show_financial_intelligence(insights):
    """Financial intelligence view"""
    st.subheader("Financial Intelligence")
    
    # Extract financial data
    financial_data = []
    
    for insight in insights:
        payment_terms = insight['analysisResults'].get('paymentTerms', [])
        party_name = insight['partyName']
        doc_id = insight['documentId']
        
        for term in payment_terms:
            description = term.get('description', 'N/A')
            amount = term.get('amount', 'N/A')
            
            financial_data.append({
                'Competitor': party_name,
                'Document': doc_id,
                'Metric': description,
                'Amount': amount
            })
    
    if financial_data:
        df_financial = pd.DataFrame(financial_data)
        
        # Display as table
        st.markdown("#### 💰 Financial Metrics")
        st.dataframe(
            df_financial,
            use_container_width=True,
            hide_index=True
        )
        
        # Funding visualization
        st.markdown("#### 📊 Funding Analysis")
        
        # Extract funding amounts
        funding_data = []
        for item in financial_data:
            if 'funding' in item['Metric'].lower() or 'series' in item['Metric'].lower():
                funding_data.append(item)
        
        if funding_data:
            df_funding = pd.DataFrame(funding_data)
            st.dataframe(df_funding, use_container_width=True, hide_index=True)
        else:
            st.info("No funding data available in current selection")
    else:
        st.info("No financial data available")

def show_risk_analysis(insights):
    """Risk analysis view"""
    st.subheader("Risk & Opportunity Analysis")
    
    # Extract risks
    all_risks = []
    
    for insight in insights:
        risks = insight['analysisResults'].get('risks', [])
        party_name = insight['partyName']
        doc_id = insight['documentId']
        
        for risk in risks:
            risk_type = risk.get('type', 'Unknown')
            description = risk.get('description', 'N/A')
            
            all_risks.append({
                'Competitor': party_name,
                'Document': doc_id,
                'Risk Type': risk_type,
                'Description': description
            })
    
    if all_risks:
        df_risks = pd.DataFrame(all_risks)
        
        # Risk type distribution
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 📊 Risk Distribution")
            risk_counts = df_risks['Risk Type'].value_counts().reset_index()
            risk_counts.columns = ['Risk Type', 'Count']
            
            fig = px.pie(
                risk_counts,
                values='Count',
                names='Risk Type',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### ⚠️ Risk Details")
            st.dataframe(
                df_risks,
                use_container_width=True,
                hide_index=True,
                height=400
            )
    else:
        st.info("No risk data available")

def show_document_explorer(insights):
    """Document explorer view"""
    st.subheader("Document Explorer")
    
    # Document selector
    doc_options = {i['documentId']: i for i in insights}
    selected_doc = st.selectbox(
        "Select a document to explore",
        options=list(doc_options.keys())
    )
    
    if selected_doc:
        insight = doc_options[selected_doc]
        
        # Document metadata
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Document ID", insight['documentId'])
            st.metric("Primary Party", insight['partyName'])
        
        with col2:
            st.metric("Effective Date", insight['effectiveDate'])
            st.metric("Environment", insight['environment'])
        
        with col3:
            # Convert Decimal to int for timestamp
            upload_ts = insight['uploadTimestamp']
            if isinstance(upload_ts, Decimal):
                upload_ts = int(upload_ts)
            upload_time = datetime.fromtimestamp(upload_ts)
            st.metric("Upload Time", upload_time.strftime("%Y-%m-%d %H:%M"))
            st.metric("Job ID", insight['jobId'][:8] + "...")
        
        st.divider()
        
        # Analysis results tabs
        analysis = insight['analysisResults']
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Parties", "Dates", "Financial", "Initiatives", "Risks"
        ])
        
        with tab1:
            st.markdown("#### 🏢 Parties & Competitors")
            parties = analysis.get('parties', [])
            if parties:
                df_parties = pd.DataFrame(parties)
                st.dataframe(df_parties, use_container_width=True, hide_index=True)
            else:
                st.info("No party data")
        
        with tab2:
            st.markdown("#### 📅 Key Dates")
            dates = analysis.get('dates', {})
            if dates:
                st.json(dates)
            else:
                st.info("No date data")
        
        with tab3:
            st.markdown("#### 💰 Financial Information")
            payment_terms = analysis.get('paymentTerms', [])
            if payment_terms:
                df_payments = pd.DataFrame(payment_terms)
                st.dataframe(df_payments, use_container_width=True, hide_index=True)
            else:
                st.info("No financial data")
        
        with tab4:
            st.markdown("#### 🎯 Strategic Initiatives")
            obligations = analysis.get('obligations', [])
            if obligations:
                df_obligations = pd.DataFrame(obligations)
                st.dataframe(df_obligations, use_container_width=True, hide_index=True)
            else:
                st.info("No initiative data")
        
        with tab5:
            st.markdown("#### ⚠️ Risks & Opportunities")
            risks = analysis.get('risks', [])
            if risks:
                df_risks = pd.DataFrame(risks)
                st.dataframe(df_risks, use_container_width=True, hide_index=True)
            else:
                st.info("No risk data")
        
        # Raw JSON view
        with st.expander("🔍 View Raw JSON"):
            st.json(json.loads(json.dumps(insight, default=decimal_to_float)))

if __name__ == "__main__":
    main()
