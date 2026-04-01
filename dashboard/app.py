import streamlit as st
import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from decimal import Decimal

st.set_page_config(
    page_title="Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* === Global dark background === */
    .stApp, .main, [data-testid="stAppViewContainer"] {
        background-color: #30325c7 !important;
        color: #d0d0d0 !important;
    }
    .main .block-container { max-width: 100% !important; padding: 12px 48px !important; }

    /* === Header === */
    .main-header { font-size: 1.3rem; font-weight: 700; color: #efefef; margin-bottom: 2px; }
    .sub-header { font-size: 0.75rem; color: #707080; margin-bottom: 12px; }

    /* === Metrics === */
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; color: #efefef !important; }
    [data-testid="stMetricLabel"] { font-size: 0.7rem !important; font-weight: 500 !important;
        color: #707080 !important; text-transform: uppercase; letter-spacing: 0.06em; }

    /* === Tabs === */
    .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #1a1a24; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; font-weight: 500; font-size: 0.8rem; color: #505060; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #8b9aff; border-bottom: 2px solid #8b9aff; }

    /* === Sidebar === */
    section[data-testid="stSidebar"] { background: #222138!important; border-right: 1px solid #454580 !important; }
    section[data-testid="stSidebar"] > div { padding: 16px !important; }
    .sidebar-section { font-size: 0.72rem; font-weight: 700; color: #8b9aff;
        text-transform: uppercase; letter-spacing: 0.08em; margin: 14px 0 6px 0; }
    [data-testid="stSidebar"] .stCheckbox label { font-size: 0.8rem !important; color: #a0a0b0 !important; }
    [data-testid="stSidebar"] .stRadio label { color: #a0a0b0 !important; }

    /* === Expanders === */
    [data-testid="stExpander"] { background-color: #0c0c14 !important; border: 1px solid #1a1a24 !important; border-radius: 6px; }
    [data-testid="stExpander"] summary { color: #c0c0d0 !important; }

    /* === Dataframes / tables === */
    [data-testid="stDataFrame"], .stDataFrame { background-color: #0c0c14 !important; }

    /* === Selectbox, inputs === */
    [data-baseweb="select"] > div { background-color: #0e0e16 !important; border-color: #1a1a24 !important; }
    [data-baseweb="input"] > div { background-color: #0e0e16 !important; border-color: #1a1a24 !important; }

    /* === Dividers === */
    hr { border-color: #1a1a24 !important; }

    /* === Hide chrome === */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_aws_clients():
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    return dynamodb.Table('market-analysis-market-insights-dev')

@st.cache_resource
def get_s3_client():
    return boto3.client('s3', region_name='us-east-1')

def decimal_to_float(obj):
    if isinstance(obj, Decimal): return float(obj)
    raise TypeError

@st.cache_data(ttl=30)
def load_insights():
    table = init_aws_clients()
    try:
        response = table.scan()
        items = response['Items']
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        return items
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return []

def parse_insights(items):
    insights = []
    for item in items:
        try:
            ts = item.get('uploadTimestamp', 0)
            if isinstance(ts, Decimal): ts = int(ts)
            insights.append({
                'insightId': item.get('insightId', 'N/A'),
                'documentId': item.get('documentId', 'N/A'),
                'jobId': item.get('jobId', 'N/A'),
                'partyName': item.get('partyName', 'Unknown'),
                'effectiveDate': item.get('effectiveDate', 'Unknown'),
                'uploadTimestamp': ts,
                'processingTimestamp': item.get('processingTimestamp', 'N/A'),
                'environment': item.get('environment', 'N/A'),
                's3Metadata': item.get('s3Metadata', {}),
                'analysisResults': item.get('analysisResults', {})
            })
        except Exception as e:
            st.warning(f"Error parsing insight: {str(e)}")
    return insights

def download_s3_document(bucket, key):
    try:
        return get_s3_client().get_object(Bucket=bucket, Key=key)['Body'].read()
    except Exception as e:
        st.error(f"Error downloading document: {str(e)}")
        return None

def main():
    st.markdown('<div class="main-header">📊 Market Intelligence Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time competitive intelligence and market insights</div>', unsafe_allow_html=True)

    # Auto-refresh: check for new items every 30 seconds
    import time
    if 'last_count' not in st.session_state:
        st.session_state.last_count = 0

    with st.spinner('Loading...'):
        items = load_insights()
        insights = parse_insights(items)

    # Detect new items and auto-refresh
    current_count = len(insights)
    if st.session_state.last_count > 0 and current_count != st.session_state.last_count:
        st.session_state.last_count = current_count
        st.cache_data.clear()
    st.session_state.last_count = current_count

    if not insights:
        st.warning("No insights found. Upload documents to S3 to generate market intelligence.")
        return

    all_docs = sorted(set(i['documentId'] for i in insights))

    # --- Sidebar: checkbox filters ---
    with st.sidebar:
        st.markdown("## 🎯 Filters")
        st.markdown("---")

        # Time period radio
        st.markdown('<div class="sidebar-section">📅 Time Period</div>', unsafe_allow_html=True)
        date_filter = st.radio("Period", ["All time", "Last 7 days", "Last 30 days", "Last 90 days"],
                               index=0, label_visibility="collapsed")
        st.markdown("---")

        # Document checkboxes
        st.markdown('<div class="sidebar-section">📄 Documents</div>', unsafe_allow_html=True)
        all_doc_on = st.checkbox("Select All", value=True, key="all_docs")
        if all_doc_on:
            selected_docs = list(all_docs)
            for doc in all_docs:
                st.checkbox(doc, value=True, key=f"doc_{doc}", disabled=True)
        else:
            selected_docs = []
            for doc in all_docs:
                checked = st.checkbox(doc, value=False, key=f"doc_{doc}")
                if checked:
                    selected_docs.append(doc)

    # Apply filters
    now_ts = int(datetime.utcnow().timestamp())
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}.get(date_filter, 0)
    cutoff = now_ts - days * 86400 if days else 0
    filtered = [i for i in insights
                if i['documentId'] in selected_docs
                and i['uploadTimestamp'] >= cutoff]

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("📄 Total Documents", len(filtered))
    all_parties = set()
    for i in filtered:
        for p in i['analysisResults'].get('parties', []):
            all_parties.add(p.get('name', 'Unknown'))
    with c2: st.metric("🏢 Competitors", len(all_parties))
    with c3: st.metric("⚠️ Risks", sum(len(i['analysisResults'].get('risks',[])) for i in filtered))
    with c4: st.metric("🎯 Initiatives", sum(len(i['analysisResults'].get('obligations',[])) for i in filtered))
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Overview", "🏢 Competitors", "💰 Financial", "⚠️ Risks", "📋 Documents"])
    with tab1: show_overview(filtered)
    with tab2: show_competitors(filtered)
    with tab3: show_financial(filtered)
    with tab4: show_risks(filtered)
    with tab5: show_documents(filtered)

    # Auto-refresh page every 30 seconds to pick up new data
    st.markdown(
        '<meta http-equiv="refresh" content="30">',
        unsafe_allow_html=True
    )

def show_overview(insights):
    st.markdown("### Market Intelligence Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 📅 Documents Processed")
        df = pd.DataFrame([{'date': datetime.fromtimestamp(i['uploadTimestamp'])} for i in insights])
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            c = df.groupby(df['date'].dt.date).size().reset_index(); c.columns = ['Date','Count']
            fig = px.line(c, x='Date', y='Count', markers=True)
            fig.update_traces(line_color='#667eea', marker=dict(size=10))
            fig.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=300,
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#909090', xaxis=dict(gridcolor='#1a1a24'),
                              yaxis=dict(gridcolor='#1a1a24'))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data")
    with col2:
        st.markdown("##### 🏢 Competitor Mentions")
        cc = {}
        for i in insights:
            for p in i['analysisResults'].get('parties', []):
                n = p.get('name','Unknown'); cc[n] = cc.get(n,0)+1
        if cc:
            df_c = pd.DataFrame(list(cc.items()), columns=['Competitor','Mentions'])
            df_c = df_c.sort_values('Mentions', ascending=False).head(10)
            fig = px.bar(df_c, x='Mentions', y='Competitor', orientation='h')
            fig.update_traces(marker_color='#764ba2')
            fig.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=300,
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font_color='#909090', xaxis=dict(gridcolor='#1a1a24'),
                              yaxis=dict(gridcolor='#1a1a24'))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data")

    st.markdown("##### 🔔 Recent Insights")
    recent = sorted(insights, key=lambda x: x['uploadTimestamp'], reverse=True)[:10]
    for idx, ins in enumerate(recent):
        s3m = ins.get('s3Metadata',{}); bucket = s3m.get('bucket',''); key = s3m.get('key','')
        doc_name = key.split('/')[-1] if key else ins['documentId']
        ar = ins['analysisResults']
        sm = f"{len(ar.get('parties',[]))} parties · {len(ar.get('risks',[]))} risks · {len(ar.get('obligations',[]))} initiatives"
        with st.expander(f"📄 {ins['documentId']} — {ins['partyName']} | {ins['effectiveDate']}"):
            st.markdown(f"**Competitor:** {ins['partyName']}  ·  **Date:** {ins['effectiveDate']}  ·  **Processed:** {ins['processingTimestamp']}")
            st.markdown(f"**Summary:** {sm}")
            if bucket and key:
                content = download_s3_document(bucket, key)
                if content:
                    st.download_button("⬇️ Download", data=content, file_name=doc_name,
                                      mime="application/octet-stream", key=f"dl_{idx}")

def show_competitors(insights):
    st.markdown("### Competitor Intelligence")
    profiles = {}
    for ins in insights:
        for party in ins['analysisResults'].get('parties', []):
            name = party.get('name','Unknown')
            if name not in profiles:
                profiles[name] = {'roles': set(), 'mentions': 0, 'initiatives': [], 'documents': []}
            profiles[name]['roles'].add(party.get('role','N/A'))
            profiles[name]['mentions'] += 1
            profiles[name]['documents'].append(ins['documentId'])
        for ob in ins['analysisResults'].get('obligations', []):
            pn = ob.get('party','')
            if pn in profiles: profiles[pn]['initiatives'].append(ob.get('obligation',''))
    for name, p in sorted(profiles.items(), key=lambda x: x[1]['mentions'], reverse=True):
        with st.expander(f"🏢 {name} ({p['mentions']} mentions)"):
            c1, c2 = st.columns([2,1])
            with c1:
                st.markdown(f"**Position:** {', '.join(p['roles'])}")
                st.markdown(f"**Documents:** {', '.join(set(p['documents']))}")
                if p['initiatives']:
                    st.markdown("**Initiatives:**")
                    for init in p['initiatives'][:5]: st.markdown(f"- {init}")
            with c2: st.metric("Mentions", p['mentions'])

def show_financial(insights):
    st.markdown("### Financial Intelligence")
    data = []
    for ins in insights:
        for t in ins['analysisResults'].get('paymentTerms', []):
            data.append({'Competitor': ins['partyName'], 'Document': ins['documentId'],
                        'Metric': t.get('description','N/A'), 'Amount': t.get('amount','N/A')})
    if data:
        df = pd.DataFrame(data)
        st.markdown("##### 💰 Financial Metrics")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else: st.info("No financial data available")

def show_risks(insights):
    st.markdown("### Risk & Opportunity Analysis")
    data = []
    for ins in insights:
        for r in ins['analysisResults'].get('risks', []):
            row = {
                'Competitor': ins['partyName'],
                'Document': ins['documentId'],
                'Risk Type': r.get('riskType', r.get('type', 'Unknown')),
                'Type': r.get('type', 'Unknown'),
                'Severity': r.get('severity', '—'),
                'Potential': r.get('potential', '—'),
                'Description': r.get('description', 'N/A')
            }
            data.append(row)
    if data:
        df = pd.DataFrame(data)
        df = df.fillna('—').replace('None', '—')
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📊 Risk Type Distribution")
            rc = df['Risk Type'].value_counts().reset_index(); rc.columns = ['Risk Type','Count']
            fig = px.pie(rc, values='Count', names='Risk Type', hole=0.4,
                        color_discrete_sequence=px.colors.sequential.RdBu)
            fig.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=300,
                              paper_bgcolor='rgba(0,0,0,0)', font_color='#909090')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("##### 📊 Risk vs Opportunity")
            ro = df['Type'].value_counts().reset_index(); ro.columns = ['Type','Count']
            fig2 = px.pie(ro, values='Count', names='Type', hole=0.4,
                         color_discrete_map={'Risk': '#ef4444', 'Opportunity': '#22c55e'})
            fig2.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=300,
                               paper_bgcolor='rgba(0,0,0,0)', font_color='#909090')
            st.plotly_chart(fig2, use_container_width=True)
        st.markdown("##### ⚠️ Details")
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    else: st.info("No risk data available")

def render_as_table(data, label=None):
    """Render any data structure as a table — never as raw JSON."""
    if label:
        st.markdown(f"**{label}**")
    if isinstance(data, list) and data:
        if isinstance(data[0], dict):
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.dataframe(pd.DataFrame({'Value': data}), use_container_width=True, hide_index=True)
    elif isinstance(data, dict) and data:
        # Flatten: collect all list-of-dicts values into one table, simple values into a key/value table
        simple_rows = []
        for k, v in data.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                st.markdown(f"**{k}**")
                st.dataframe(pd.DataFrame(v), use_container_width=True, hide_index=True)
            elif isinstance(v, list) and v:
                for item in v:
                    simple_rows.append({'Field': k, 'Value': str(item)})
            elif isinstance(v, dict) and v:
                for fk, fv in v.items():
                    simple_rows.append({'Field': f"{k}.{fk}", 'Value': str(fv) if fv else 'N/A'})
            else:
                simple_rows.append({'Field': k, 'Value': str(v) if v else 'N/A'})
        if simple_rows:
            st.dataframe(pd.DataFrame(simple_rows), use_container_width=True, hide_index=True)
    elif data:
        st.write(str(data))
    else:
        st.info("No data")

def show_documents(insights):
    st.markdown("### Document Explorer")
    doc_map = {i['documentId']: i for i in insights}
    sel = st.selectbox("Select a document", options=list(doc_map.keys()))
    if not sel: return
    ins = doc_map[sel]
    s3m = ins.get('s3Metadata',{}); bucket = s3m.get('bucket',''); key = s3m.get('key','')
    doc_name = key.split('/')[-1] if key else sel

    c1, c2, c3 = st.columns([2,2,1])
    with c1:
        st.metric("Document", ins['documentId']); st.metric("Party", ins['partyName'])
    with c2:
        st.metric("Effective Date", ins['effectiveDate'])
        ts = ins['uploadTimestamp']
        if isinstance(ts, Decimal): ts = int(ts)
        st.metric("Uploaded", datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"))
    with c3:
        if bucket and key:
            content = download_s3_document(bucket, key)
            if content:
                st.download_button("⬇️ Download", data=content, file_name=doc_name,
                                  mime="application/octet-stream", key="exp_dl")
    st.divider()
    a = ins['analysisResults']

    t1,t2,t3,t4,t5 = st.tabs(["Parties","Dates","Financial","Initiatives","Risks"])
    with t1:
        st.markdown("##### 🏢 Parties & Competitors")
        render_as_table(a.get('parties',[]))
    with t2:
        dates = a.get('dates', {})
        if not dates:
            st.info("No date information available for this document.")
        else:
            # Recursively extract all date entries into a flat list
            def flatten_dates(data, prefix=''):
                import re
                date_pattern = re.compile(r'^\d{4}[-/]\d{2}([-/]\d{2})?$')
                def make_row(d, e, cat=None):
                    # Auto-detect: if event looks like a date and date doesn't, swap them
                    d_str, e_str = str(d), str(e)
                    if date_pattern.match(e_str) and not date_pattern.match(d_str):
                        d_str, e_str = e_str, d_str
                    row = {'Event': e_str, 'Date': d_str}
                    if cat: row['Category'] = cat
                    return row
                rows = []
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            d = item.get('date', '')
                            e = item.get('event', item.get('description', str(item)))
                            rows.append(make_row(d, e))
                        else:
                            rows.append(make_row('', item))
                elif isinstance(data, dict):
                    for k, v in data.items():
                        if k in ('effectiveDate', 'terminationDate'):
                            continue
                        lbl = k[0].upper() + k[1:]
                        lbl = ''.join(' ' + c if c.isupper() else c for c in lbl).strip()
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict):
                                    d = item.get('date', '')
                                    e = item.get('event', item.get('description', str(item)))
                                    rows.append(make_row(d, e, lbl))
                                else:
                                    rows.append(make_row('', item, lbl))
                        elif isinstance(v, dict):
                            for fk, fv in v.items():
                                fl = fk[0].upper() + fk[1:]
                                fl = ''.join(' ' + c if c.isupper() else c for c in fl).strip()
                                if isinstance(fv, list):
                                    for item in fv:
                                        if isinstance(item, dict):
                                            d = item.get('date', '')
                                            e = item.get('event', item.get('description', str(item)))
                                            rows.append(make_row(d, e, fl))
                                        else:
                                            rows.append(make_row('', item, fl))
                                else:
                                    rows.append(make_row(str(fv) if fv else 'N/A', fl, lbl))
                        else:
                            rows.append(make_row(str(v) if v else 'N/A', lbl))
                return rows

            all_rows = flatten_dates(dates)
            if all_rows:
                df = pd.DataFrame(all_rows)
                # If Category column exists, show grouped tables
                if 'Category' in df.columns:
                    for cat in df['Category'].unique():
                        st.markdown(f"##### 📅 {cat}")
                        cat_df = df[df['Category'] == cat][['Event', 'Date']].sort_values('Date')
                        st.dataframe(cat_df, use_container_width=True, hide_index=True)
                else:
                    st.markdown("##### 📅 Key Dates")
                    df = df[['Event', 'Date']].sort_values('Date')
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No date information available.")
    with t3:
        st.markdown("##### 💰 Financial Information")
        render_as_table(a.get('paymentTerms',[]))
    with t4:
        st.markdown("##### 🎯 Strategic Initiatives")
        render_as_table(a.get('obligations',[]))
    with t5:
        st.markdown("##### ⚠️ Risks & Opportunities")
        risks = a.get('risks', [])
        if risks:
            df = pd.DataFrame(risks)
            # Enforce column order
            col_order = [c for c in ['type', 'riskType', 'severity', 'potential', 'description'] if c in df.columns]
            # Add any extra columns not in the preferred order
            col_order += [c for c in df.columns if c not in col_order]
            df = df[col_order]
            # Replace None/NaN with dash
            df = df.fillna('—')
            df = df.replace('None', '—')
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No risk data")

if __name__ == "__main__":
    main()
