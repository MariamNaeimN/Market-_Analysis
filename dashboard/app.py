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
    initial_sidebar_state="collapsed"  # Start collapsed for more space
)

# Custom CSS for ultra-minimal design (4px grid system)
st.markdown("""
<style>
    /* Ultra-minimal Design System - 4px Grid */
    :root {
        --space-1: 4px;
        --space-2: 8px;
        --space-3: 12px;
        --space-4: 16px;
        --sidebar-width: 320px;
    }
    
    /* Override Streamlit's default layout to prevent sidebar spacing issues */
    section.main {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    
    /* Force main content container to use full available width */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 48px !important;
        padding-right: 48px !important;
        padding-top: var(--space-3) !important;
        padding-bottom: var(--space-3) !important;
    }
    
    /* Remove any default margins from Streamlit */
    .stApp {
        margin-left: 0 !important;
    }
    
    /* Minimal header */
    .main-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 2px;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-size: 0.7rem;
        color: #909090;
        margin-bottom: var(--space-3);
        font-weight: 400;
    }
    
    /* Ultra-compact metrics */
    .stMetric {
        background: transparent !important;
        padding: 0 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.65rem !important;
        font-weight: 500 !important;
        color: #909090 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.6rem !important;
    }
    
    /* Minimal tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
        border-bottom: 1px solid #252530;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 6px var(--space-3);
        font-weight: 500;
        font-size: 0.75rem;
        color: #707070;
        background: transparent;
        border: none;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #8b9aff;
        border-bottom: 1px solid #8b9aff;
    }
    
    /* Minimal insight cards */
    .insight-card {
        background: transparent;
        padding: var(--space-2) 0;
        border-bottom: 1px solid #1a1a20;
        margin-bottom: 0;
    }
    .insight-card:hover {
        background: #0a0a0f;
    }
    .insight-card h4 {
        color: #ffffff;
        font-size: 0.75rem;
        margin-bottom: var(--space-1);
        font-weight: 600;
    }
    .insight-card p {
        color: #a0a0a0;
        font-size: 0.7rem;
        margin: 2px 0;
        line-height: 1.3;
        font-weight: 400;
    }
    .insight-card strong {
        color: #d0d0d0;
        font-weight: 500;
    }
    
    /* Minimal sidebar with smooth transitions */
    section[data-testid="stSidebar"] {
        background: #0a0a0f !important;
        border-right: 1px solid #1a1a20 !important;
        width: var(--sidebar-width) !important;
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    section[data-testid="stSidebar"] > div {
        width: var(--sidebar-width) !important;
        padding: var(--space-3) !important;
    }
    
    /* When sidebar is collapsed */
    section[data-testid="stSidebar"][aria-expanded="false"] {
        width: 0 !important;
        min-width: 0 !important;
        transform: translateX(-100%);
        border-right: none !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] > div {
        display: none;
    }
    
    /* Sidebar toggle button - always visible */
    button[kind="header"] {
        position: fixed !important;
        top: var(--space-3) !important;
        left: var(--space-3) !important;
        z-index: 999999 !important;
        background: #1a1a20 !important;
        border: 1px solid #2a2a30 !important;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    
    button[kind="header"]:hover {
        background: #2a2a30 !important;
        border-color: #667eea !important;
        transform: scale(1.05);
    }
    
    /* When sidebar is open, move toggle button */
    section[data-testid="stSidebar"][aria-expanded="true"] ~ div button[kind="header"] {
        left: calc(var(--sidebar-width) + var(--space-3)) !important;
    }
    
    /* Sidebar content */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: var(--space-2);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    [data-testid="stSidebar"] .stMarkdown {
        font-size: 0.8rem;
        color: #b0b0b0;
        line-height: 1.4;
    }
    [data-testid="stSidebar"] .stMarkdown strong {
        color: #8b9aff;
        font-weight: 600;
        font-size: 0.75rem;
    }
    [data-testid="stSidebar"] hr {
        margin: var(--space-3) 0;
        border-color: #1a1a20;
        opacity: 1;
    }
    
    /* Minimal sidebar inputs */
    [data-testid="stSidebar"] label {
        font-size: 0.7rem !important;
        font-weight: 500 !important;
        color: #a0a0a0 !important;
    }
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stMultiSelect {
        margin-bottom: var(--space-2);
    }
    [data-testid="stSidebar"] [data-baseweb="select"] {
        font-size: 0.8rem !important;
        background: transparent !important;
        border: 1px solid #1a1a20 !important;
        min-height: 30px !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"]:hover {
        border-color: #667eea !important;
    }
    
    /* Multiselect container - use flexbox with wrapping */
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 12px !important;
        padding: 12px !important;
        min-height: auto !important;
        max-height: none !important;
        overflow-y: visible !important;
        align-items: flex-start !important;
        background: #151520 !important;
        border-radius: 6px !important;
    }
    
    /* Minimal multiselect tags - compact chip design with full text visibility */
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        font-size: 0.75rem !important;
        background: #667eea !important;
        color: white !important;
        padding: 7px 14px !important;
        margin: 0 !important;
        border-radius: 6px !important;
        height: auto !important;
        min-height: 30px !important;
        display: inline-flex !important;
        align-items: center !important;
        white-space: normal !important;
        word-break: break-word !important;
        flex-shrink: 0 !important;
        max-width: 100% !important;
        line-height: 1.4 !important;
        overflow: visible !important;
        text-overflow: clip !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
    }
    
    /* Tag text - full visibility */
    [data-testid="stSidebar"] [data-baseweb="tag"] span {
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: normal !important;
        word-break: break-word !important;
        max-width: 100% !important;
    }
    
    /* Tag close button */
    [data-testid="stSidebar"] [data-baseweb="tag"] svg {
        width: 14px !important;
        height: 14px !important;
        margin-left: 6px !important;
        flex-shrink: 0 !important;
    }
        flex-shrink: 0 !important;
        max-width: 100% !important;
    }
    
    /* Tag text - prevent truncation */
    [data-testid="stSidebar"] [data-baseweb="tag"] span {
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
    }
    
    /* Tag close button */
    [data-testid="stSidebar"] [data-baseweb="tag"] svg {
        width: 14px !important;
        height: 14px !important;
        margin-left: 4px !important;
    }
    
    /* Sidebar caption */
    [data-testid="stSidebar"] .stCaption {
        font-size: 0.65rem !important;
        color: #707070;
        margin-bottom: var(--space-1);
    }
    
    /* Sidebar metric */
    [data-testid="stSidebar"] .stMetric {
        background: transparent;
        padding: var(--space-2);
        border: 1px solid #1a1a20;
        border-radius: 4px;
    }
    
    /* Sidebar button */
    [data-testid="stSidebar"] .stButton button {
        font-size: 0.75rem;
        padding: 7px var(--space-2);
        background: #667eea;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 500;
        width: 100%;
        height: 30px;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: #5568d3;
    }
    
    /* Sidebar collapse button enhancement */
    button[kind="header"] svg {
        width: 20px;
        height: 20px;
    }
    
    /* Minimal typography */
    h1 { font-size: 1rem !important; font-weight: 600 !important; color: #ffffff; margin-bottom: var(--space-2); }
    h2 { font-size: 0.9rem !important; font-weight: 600 !important; color: #ffffff; margin-bottom: var(--space-2); }
    h3 { font-size: 0.8rem !important; font-weight: 600 !important; color: #e0e0e0; margin-bottom: var(--space-1); }
    h4 { font-size: 0.75rem !important; font-weight: 500 !important; color: #d0d0d0; margin-bottom: var(--space-1); }
    h5 { font-size: 0.7rem !important; font-weight: 500 !important; color: #c0c0c0; margin-bottom: var(--space-1); }
    
    /* Minimal dataframes */
    .dataframe {
        font-size: 0.7rem !important;
        font-weight: 400;
    }
    .dataframe th {
        background: transparent !important;
        color: #909090 !important;
        font-weight: 600 !important;
        font-size: 0.65rem !important;
        padding: var(--space-1) var(--space-2) !important;
        border-bottom: 1px solid #1a1a20 !important;
    }
    .dataframe td {
        padding: var(--space-1) var(--space-2) !important;
        border-bottom: 1px solid #0a0a0f !important;
    }
    
    /* Minimal expander */
    .streamlit-expanderHeader {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        background: transparent !important;
        border: 1px solid #1a1a20 !important;
        border-radius: 4px !important;
        padding: var(--space-2) !important;
    }
    
    /* Minimal buttons */
    .stButton button {
        font-size: 0.7rem;
        font-weight: 500;
        padding: 6px var(--space-3);
        border-radius: 4px;
    }
    
    /* Minimal divider */
    hr {
        margin: var(--space-3) 0;
        border-color: #1a1a20;
        opacity: 1;
    }
    
    /* Remove all shadows */
    * {
        box-shadow: none !important;
    }
    
    /* Minimal spacing */
    .element-container {
        margin-bottom: var(--space-1) !important;
    }
    
    /* Compact charts */
    .js-plotly-plot {
        margin-bottom: var(--space-2) !important;
    }
    
    /* Smooth transitions for layout changes */
    .main, [data-testid="stSidebar"], .block-container {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Responsive behavior */
    @media (max-width: 768px) {
        :root {
            --sidebar-width: 240px;
        }
        section[data-testid="stSidebar"] {
            width: 240px !important;
        }
        section[data-testid="stSidebar"] > div {
            width: 240px !important;
        }
    }
</style>

<script>
    // Dynamically adjust main content padding based on sidebar state
    function adjustMainContent() {
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        const main = document.querySelector('section.main');
        const body = document.body;
        
        if (sidebar && main) {
            const isExpanded = sidebar.getAttribute('aria-expanded') === 'true';
            
            if (isExpanded) {
                body.classList.add('sidebar-open');
                body.classList.remove('sidebar-closed');
            } else {
                body.classList.add('sidebar-closed');
                body.classList.remove('sidebar-open');
            }
        }
    }
    
    // Initial adjustment
    setTimeout(adjustMainContent, 100);
    
    // Watch for sidebar state changes
    const observer = new MutationObserver(adjustMainContent);
    
    function startWatching() {
        const sidebar = document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            observer.observe(sidebar, { 
                attributes: true, 
                attributeFilter: ['aria-expanded'] 
            });
            adjustMainContent();
        } else {
            setTimeout(startWatching, 100);
        }
    }
    
    startWatching();
    
    // Re-adjust on Streamlit reruns
    window.addEventListener('load', adjustMainContent);
    document.addEventListener('DOMContentLoaded', adjustMainContent);
</script>
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
    with st.sidebar:
        st.markdown("### 🎯 Filters")
        st.markdown("---")
        
        # Date range filter
        st.markdown("**📅 Time Period**")
        date_options = ["Last 7 days", "Last 30 days", "Last 90 days", "All time"]
        date_filter = st.selectbox(
            "Period",
            date_options,
            index=1,
            label_visibility="collapsed"
        )
        
        st.markdown("")  # Spacing
        
        # Competitor filter
        st.markdown("**🏢 Competitors**")
        all_competitors = sorted(list(set([i['partyName'] for i in insights if i['partyName'] != 'Unknown'])))
        
        # Show count
        st.caption(f"{len(all_competitors)} competitors available")
        
        selected_competitors = st.multiselect(
            "Select competitors to analyze",
            options=all_competitors,
            default=all_competitors[:5] if len(all_competitors) > 5 else all_competitors,
            label_visibility="collapsed"
        )
        
        st.markdown("")  # Spacing
        
        # Document type filter
        st.markdown("**📄 Document Types**")
        doc_types = sorted(list(set([i['documentId'] for i in insights])))
        
        # Show count
        st.caption(f"{len(doc_types)} document types")
        
        selected_docs = st.multiselect(
            "Select document types",
            options=doc_types,
            default=doc_types,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Summary stats in sidebar
        st.markdown("**📊 Quick Stats**")
        st.metric("Total Insights", len(insights), delta=None)
        
        # Refresh button
        st.markdown("")
        if st.button("🔄 Refresh Data", use_container_width=True, key="refresh_button"):
            st.cache_data.clear()
            st.rerun()
    
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
    st.markdown("### Market Intelligence Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Documents processed over time
        st.markdown("##### 📅 Documents Processed Timeline")
        
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
        st.markdown("##### 🏢 Competitor Mentions")
        
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
    st.markdown("##### 🔔 Recent Insights")
    
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
    st.markdown("### Competitor Intelligence")
    
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
    st.markdown("### Financial Intelligence")
    
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
        st.markdown("##### 💰 Financial Metrics")
        st.dataframe(
            df_financial,
            use_container_width=True,
            hide_index=True
        )
        
        # Funding visualization
        st.markdown("##### 📊 Funding Analysis")
        
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
    st.markdown("### Risk & Opportunity Analysis")
    
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
            st.markdown("##### 📊 Risk Distribution")
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
            st.markdown("##### ⚠️ Risk Details")
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
    st.markdown("### Document Explorer")
    
    # Document selector
    doc_options = {i['documentId']: i for i in insights}
    selected_doc = st.selectbox(
        "Select a document to explore",
        options=list(doc_options.keys())
    )
    
    if selected_doc:
        insight = doc_options[selected_doc]
        
        # Document metadata
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Document ID", insight['documentId'])
            st.metric("Primary Party", insight['partyName'])
        
        with col2:
            st.metric("Effective Date", insight['effectiveDate'])
            # Convert Decimal to int for timestamp
            upload_ts = insight['uploadTimestamp']
            if isinstance(upload_ts, Decimal):
                upload_ts = int(upload_ts)
            upload_time = datetime.fromtimestamp(upload_ts)
            st.metric("Upload Time", upload_time.strftime("%Y-%m-%d %H:%M"))
        
        st.divider()
        
        # Analysis results tabs
        analysis = insight['analysisResults']
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Parties", "Dates", "Financial", "Initiatives", "Risks"
        ])
        
        with tab1:
            st.markdown("##### 🏢 Parties & Competitors")
            parties = analysis.get('parties', [])
            if parties:
                df_parties = pd.DataFrame(parties)
                st.dataframe(df_parties, use_container_width=True, hide_index=True)
            else:
                st.info("No party data")
        
        with tab2:
            st.markdown("##### 📅 Key Dates")
            dates = analysis.get('dates', {})
            if dates:
                st.json(dates)
            else:
                st.info("No date data")
        
        with tab3:
            st.markdown("##### 💰 Financial Information")
            payment_terms = analysis.get('paymentTerms', [])
            if payment_terms:
                df_payments = pd.DataFrame(payment_terms)
                st.dataframe(df_payments, use_container_width=True, hide_index=True)
            else:
                st.info("No financial data")
        
        with tab4:
            st.markdown("##### 🎯 Strategic Initiatives")
            obligations = analysis.get('obligations', [])
            if obligations:
                df_obligations = pd.DataFrame(obligations)
                st.dataframe(df_obligations, use_container_width=True, hide_index=True)
            else:
                st.info("No initiative data")
        
        with tab5:
            st.markdown("##### ⚠️ Risks & Opportunities")
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
