import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Emulator Host for local dev BEFORE importing scrapers
if not os.getenv("PUBSUB_EMULATOR_HOST"):
    os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"

from sqlalchemy import create_engine
from intelligence_api.core.config import settings
import requests

st.set_page_config(page_title="Omnisight OSINT Dashboard", layout="wide")

# Initialize session state for navigation and selection
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "Company"
if "selected_entity" not in st.session_state:
    st.session_state["selected_entity"] = "All"
if "selected_entity_type" not in st.session_state:
    st.session_state["selected_entity_type"] = "All"

# Helper to change selection and view
def select_entity(entity_label, entity_type, target_view=None):
    st.session_state["selected_entity"] = entity_label
    st.session_state["selected_entity_type"] = entity_type
    if target_view:
        st.session_state["view_mode"] = target_view
    st.rerun()

API_BASE = "http://localhost:8000"

# Database Connection
engine = create_engine(settings.DATABASE_URL)

# PDF Reporting Utility (Inlined to ensure Streamlit hot-reloading)
def get_pdf_bytes(title, data):
    from fpdf import FPDF
    from datetime import datetime
    
    class PDFReport(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, 'Omnisight Intelligence Export', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    try:
        pdf = PDFReport()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, f"{title}", 0, 1)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict): continue
            
            # Safe lookups for any key variation
            src = item.get('source') or item.get('source_type') or item.get('Source') or "General Intelligence"
            sent = item.get('sentiment') or item.get('sentiment_score') or item.get('Sentiment') or 0.0
            
            # Event vs Summary detection
            if item.get('content') or item.get('summary') or item.get('Text'):
                pdf.set_font('Helvetica', 'B', 11)
                pdf.multi_cell(0, 10, f"Source: {src} | Sentiment: {sent}")
                pdf.set_font('Helvetica', '', 10)
                txt = item.get('content') or item.get('summary') or item.get('Text')
                pdf.multi_cell(0, 8, "".join(i for i in str(txt) if ord(i) < 128))
                pdf.ln(5)
            else:
                for k, v in item.items():
                    k_disp = str(k).replace('_', ' ').capitalize()
                    v_str = str(v)
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.write(10, f"{k_disp}: ")
                    pdf.set_font('Helvetica', '', 10)
                    pdf.write(10, f"{v_str}\n")
                pdf.ln(5)
        
        out = pdf.output(dest='S')
        if isinstance(out, str):
            return out.encode('latin-1', 'ignore')
        return bytes(out)
    except Exception as e:
        return bytes(f"PDF Error: {str(e)}", "utf-8")


def get_dashboard_data(filter_entity: str = None, filter_source: str = "All", filter_cat: str = "All", filter_type: str = "All", filter_campaign: str = "All", sentiment_range: tuple = (-1.0, 1.0)):

    query = """
    SELECT e.label as entity, e.type as entity_type, ev.source_type, ev.sentiment_score, ev.summary, ev.category, ev.content, ev.raw_url, ev.published_at, ev.created_at, st.campaign
    FROM events ev
    JOIN entities e ON ev.entity_id = e.id
    LEFT JOIN scrape_targets st ON e.label = st.target_name
    WHERE 1=1
    """
    params = {}
    
    if filter_entity and filter_entity != "All":
        query += " AND e.label ILIKE %(entity)s"
        params["entity"] = f"%{filter_entity}%"
    
    if filter_source != "All":
        query += " AND ev.source_type = %(source)s"
        params["source"] = filter_source
        
    if filter_cat != "All":
        query += " AND ev.category = %(cat)s"
        params["cat"] = filter_cat

    if filter_type != "All":
        query += " AND e.type = %(type)s"
        params["type"] = filter_type

    if filter_campaign != "All":
        query += " AND st.campaign = %(camp)s"
        params["camp"] = filter_campaign

    query += " AND ev.sentiment_score BETWEEN %(sent_min)s AND %(sent_max)s"
    params["sent_min"] = float(sentiment_range[0])
    params["sent_max"] = float(sentiment_range[1])
    
    query += " ORDER BY ev.created_at DESC LIMIT 100"
    return pd.read_sql(query, engine, params=params)

st.title("🛡️ Omnisight OSINT")
st.markdown("---")

# Sidebar: View Navigation
st.sidebar.header("🧭 Navigation")
nav_mode = st.sidebar.radio(
    "Select View", 
    ["Topic Analysis", "Company Intelligence", "People Watch", "Knowledge Graph"],
    index=["Topic Analysis", "Company Intelligence", "People Watch", "Knowledge Graph"].index(
        "Topic Analysis" if st.session_state["view_mode"] == "Topic" else 
        "Company Intelligence" if st.session_state["view_mode"] == "Company" else 
        "Knowledge Graph" if st.session_state["view_mode"] == "Graph" else
        "People Watch"
    )
)

if nav_mode == "Topic Analysis": st.session_state["view_mode"] = "Topic"
elif nav_mode == "Company Intelligence": st.session_state["view_mode"] = "Company"
elif nav_mode == "People Watch": st.session_state["view_mode"] = "People"
elif nav_mode == "Knowledge Graph": st.session_state["view_mode"] = "Graph"

st.sidebar.markdown("---")
st.sidebar.header("🔍 Advanced Filters")

# Fetch unique entities for the filter
try:
    entities_query = "SELECT DISTINCT label FROM entities WHERE label IS NOT NULL"
    available_entities = ["All"] + pd.read_sql(entities_query, engine)['label'].tolist()
except:
    available_entities = ["All"]

# Handle filters in session state
search_term = st.sidebar.selectbox("Specific Entity", available_entities, index=available_entities.index(st.session_state["selected_entity"]) if st.session_state["selected_entity"] in available_entities else 0)
st.session_state["selected_entity"] = search_term

entity_type_filter = "All"
if st.session_state["view_mode"] == "Company":
    entity_type_filter = "COMPANY"
elif st.session_state["view_mode"] == "People":
    entity_type_filter = "USER" # Or "PERSON" if that's the type
else:
    entity_type_filter = st.sidebar.selectbox("Entity Type", ["All", "COMPANY", "USER"], index=["All", "COMPANY", "USER"].index(st.session_state["selected_entity_type"]))
    st.session_state["selected_entity_type"] = entity_type_filter

source_filter = st.sidebar.selectbox("Source Type", ["All", "Google News", "Reddit", "Nitter", "RSS"])

# Fetch unique categories for the filter
try:
    cats_query = "SELECT DISTINCT category FROM events WHERE category IS NOT NULL"
    available_cats = ["All"] + pd.read_sql(cats_query, engine)['category'].tolist()
except:
    available_cats = ["All"]

try:
    camps_query = "SELECT DISTINCT campaign FROM scrape_targets WHERE campaign IS NOT NULL"
    available_camps = ["All"] + pd.read_sql(camps_query, engine)['campaign'].dropna().tolist()
except:
    available_camps = ["All"]

cat_filter = st.sidebar.selectbox("Event Category/Topic", available_cats)
campaign_filter = st.sidebar.selectbox("Tracker Campaign", available_camps)
sent_range = st.sidebar.slider("Sentiment Range", -1.0, 1.0, (-1.0, 1.0))

st.sidebar.markdown("---")
st.sidebar.header("🚀 Configure New Tracker")
with st.sidebar.form("new_tracker_form"):
    new_target = st.text_input("New Target (Username/Topic/Subreddit)")
    target_type = st.selectbox("Source", ["Google News", "Reddit Subreddit", "Nitter/X User"])
    campaign_tag = st.text_input("Campaign/Grouping Tag (Optional)", help="Group related tracking goals together")
    
    st.markdown("**Scraping Interval**")
    colA, colB = st.columns(2)
    with colA:
        int_hours = st.number_input("Hours", min_value=0, max_value=720, value=1)
    with colB:
        int_mins = st.number_input("Minutes", min_value=0, max_value=59, value=0)
    
    submit_tracker = st.form_submit_button("Start Tracking")
    
    # Optional parameters based on source
    google_news_period = None
    if target_type == "Google News":
        google_news_period = st.selectbox(
            "Data History (Time Range)", 
            ["Latest Only", "7 Days", "30 Days", "3 Months", "6 Months", "1 Year"],
            help="Choose how far back to look in Google News. Note: RSS feeds are best for recent data (7-30d)."
        )

if submit_tracker:
    try:
        total_mins = (int_hours * 60) + int_mins
        
        # Build Scraper Params
        scraper_params = {}
        if target_type == "Google News" and google_news_period != "Latest Only":
            if google_news_period == "7 Days": scraper_params["period"] = "7d"
            elif google_news_period == "30 Days": scraper_params["period"] = "30d"
            elif google_news_period == "3 Months": scraper_params["period"] = "3m"
            elif google_news_period == "6 Months": scraper_params["period"] = "6m"
            elif google_news_period == "1 Year": scraper_params["period"] = "1y"

            
        payload = {
            "target_name": new_target,
            "source_type": target_type,
            "scrape_interval_minutes": total_mins,
            "campaign": campaign_tag if campaign_tag else None,
            "scraper_params": scraper_params if scraper_params else None
        }
        res = requests.post(f"{API_BASE}/targets", json=payload)
        res.raise_for_status()
        st.sidebar.success(f"Started tracking '{new_target}' every {int_hours}h {int_mins}m!")
        st.toast("Tracker registered with Scheduler! Refresh the 'Active Trackers' view.", icon="📡")
    except Exception as e:
        st.sidebar.error(f"Failed to configure tracker: {e}")

# Dashboard Logic
st.header("📡 Active Trackers")

try:
    res = requests.get(f"{API_BASE}/targets")
    if res.status_code == 200:
        targets = res.json()
        if targets:
            df_targets = pd.DataFrame(targets)
            
            # Format display
            # Convert metadata_json to a readable string for 'period' if it exists
            df_targets["lookback"] = df_targets["metadata_json"].apply(lambda x: x.get("period") if isinstance(x, dict) else "Default")
            
            display_cols = ["target_name", "source_type", "lookback", "campaign", "interval", "status", "next_scrape"]
            df_targets["interval"] = df_targets["interval"].apply(lambda x: f"{int(x)//60}h {int(x)%60}m")
            
            st.dataframe(
                df_targets[display_cols],
                width='stretch',
                hide_index=True,
                column_config={
                    "target_name": st.column_config.TextColumn("Target"),
                    "status": st.column_config.TextColumn(
                        "Status",
                        help="Current state of the background scraper"
                    ),
                    "next_scrape": st.column_config.DatetimeColumn(
                        "Next Planned Scrape",
                        format="D MMM YYYY, h:mm a"
                    )
                }
            )
            
            # Tracker Management & Selection
            st.divider()
            
            # Use two main columns: one for View/Quick Analysis, one for Management
            col_view, col_manage = st.columns([1, 1])
            
            with col_view:
                st.subheader("👁️ Quick Analysis")
                selected_for_view = st.selectbox("Select Tracker to View Details", df_targets["target_name"].tolist())
                if st.button("Analyze Now", width='stretch'):
                    # Find type
                    t_type = df_targets[df_targets["target_name"] == selected_for_view]["source_type"].values[0]
                    # Map source_type to entity type (rough heuristic)
                    e_type = "COMPANY"
                    if "Nitter" in t_type or "Reddit" in t_type: e_type = "USER"
                    
                    v_mode = "Company" if e_type == "COMPANY" else "People"
                    select_entity(selected_for_view, e_type, v_mode)

            with col_manage:
                st.subheader("⚙️ Manage Active Trackers")
                selected_target_name = st.selectbox("Select Tracker to Manage", df_targets["target_name"].tolist(), key="manage_select")
                target_id = df_targets[df_targets["target_name"] == selected_target_name]["id"].values[0]
                
                m1, m2 = st.columns(2)
                with m1:
                    if st.button("🚀 Run Now", width='stretch', key=f"run_{target_id}"):
                        res = requests.post(f"{API_BASE}/targets/{target_id}/run")
                        if res.status_code == 200:
                            st.success("Scrape triggered!")
                            st.rerun()
                with m2:
                    if st.button("🗑️ Delete", width='stretch', key=f"del_{target_id}"):
                        res = requests.delete(f"{API_BASE}/targets/{target_id}")
                        if res.status_code == 200:
                            st.toast("Target and all associated data deleted!", icon="🗑️")
                            st.rerun()

        else:
            st.info("No active trackers. Add one from the sidebar!")
    else:
        st.error("Failed to fetch trackers from API.")
except Exception as e:
    st.error(f"Tracker error: {e}")

st.markdown("---")
# ──────────────── Main Content Area ────────────────

if st.session_state["view_mode"] == "Topic":
    st.header("📊 Global Topic Analysis")
    try:
        df = get_dashboard_data("All", source_filter, cat_filter, "All", campaign_filter, sent_range)
        if df.empty:
            st.info("No data found for topic analysis.")
        else:
            # KPI Row
            ck1, ck2, ck3 = st.columns(3)
            with ck1: st.metric("Total Mentions", len(df))
            with ck2: st.metric("Avg Sentiment", f"{df['sentiment_score'].mean():.2f}")
            with ck3: 
                modes = df['category'].mode()
                st.metric("Top Trend", modes[0] if not modes.empty else "None")

            # Charts
            st.subheader("Global Intelligence Trends")
            c1, c2 = st.columns(2)
            with c1:
                df_trends = df.dropna(subset=['published_at']).sort_values('published_at')
                fig = px.line(df_trends, x='published_at', y='sentiment_score', color='entity', title="Sentiment Over Time")
                st.plotly_chart(fig, width='stretch')
            with c2:
                fig_cat = px.pie(df, names='category', title="Topic Distribution")
                st.plotly_chart(fig_cat, width='stretch')
    except Exception as e:
        st.error(f"Topic analysis error: {e}")

elif st.session_state["view_mode"] == "Company":
    st.header(f"🏢 Company Intelligence: {st.session_state['selected_entity']}")
    
    # 1. Sector Heatmap (Contextual Context)
    try:
        res = requests.get(f"{API_BASE}/market/sector-heatmap")
        if res.status_code == 200:
            sectors = res.json().get("sectors", [])
            if sectors:
                st.subheader("🗺️ Industry Sentiment Context")
                df_sectors = pd.DataFrame(sectors)
                fig_heatmap = px.bar(df_sectors, x='sector', y='avg_sentiment', color='avg_sentiment', 
                                    color_continuous_scale="RdYlGn", range_color=[-1, 1],
                                    title="Sector Sentiment Heatmap")
                st.plotly_chart(fig_heatmap, width='stretch')
                st.caption("Average global sentiment across relevant industry sectors.")
    except: pass

    # 2. Market Correlation Engine
    st.divider()
    st.subheader("📈 Market Correlation Analysis")
    st.caption("Overlay OSINT sentiment against stock price to detect leading signals")
    
    # Use selected_entity if it's not "All", otherwise show selector
    m_company = st.session_state["selected_entity"]
    if m_company == "All":
        try:
            c_query = "SELECT DISTINCT label FROM entities WHERE type = 'COMPANY' AND label IS NOT NULL ORDER BY label"
            m_companies = pd.read_sql(c_query, engine)['label'].tolist()
            m_company = st.selectbox("Select Company for Analysis", m_companies, key="m_sel")
        except: m_company = None
    
    if m_company:
        col_m1, col_m2 = st.columns([1, 1])
        with col_m1:
            m_lookback = st.selectbox("Lookback Period", [30, 60, 90, 180], index=2, key="m_days")
        with col_m2:
            st.write("") # Padding
            if st.button("🔍 Run Correlation Analysis", width='stretch'):
                with st.spinner(f"Analyzing {m_company}..."):
                    try:
                        res = requests.get(f"{API_BASE}/market/correlation/{m_company}", params={"days": m_lookback})
                        if res.status_code == 200:
                            st.session_state["correlation_result"] = res.json()
                        else:
                            st.error(f"Correlation failed: {res.text}")
                    except Exception as e: st.error(f"Error: {e}")

        # Display correlation results
        if "correlation_result" in st.session_state and st.session_state["correlation_result"].get("entity_label") == m_company:
            corr = st.session_state["correlation_result"]
            
            if corr.get("insight"): st.info(f"💡 **{corr['insight']}**")
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Ticker", corr.get("ticker_symbol", "N/A"))
            k2.metric("Pearson r", f"{corr.get('pearson_r', 0):+.3f}", help="Correlation coefficient (-1 to 1). 1 means moving together; -1 means opposite directions.")
            k3.metric("Best Lag", f"{corr.get('best_lag_days', 0)} days", help="Time delay with highest correlation.")
            k4.metric("Data Points", corr.get("data_points", 0), help="Number of overlapping dates.")

            # Dual-axis chart & Gauge Row
            aligned = corr.get("aligned_data", [])
            if aligned:
                df_aligned = pd.DataFrame(aligned)
                df_aligned["date"] = pd.to_datetime(df_aligned["date"])
                
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                
                col_chart, col_gauge = st.columns([3, 1])

                with col_chart:
                    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
                    # Sentiment
                    fig_dual.add_trace(go.Scatter(
                        x=df_aligned["date"], y=df_aligned["sentiment"], 
                        name="OSINT Sentiment", fill="tozeroy", 
                        fillcolor="rgba(31, 119, 180, 0.15)",
                        line=dict(color="#1f77b4", width=2)
                    ), secondary_y=False)
                    # Price
                    fig_dual.add_trace(go.Scatter(
                        x=df_aligned["date"], y=df_aligned["close_price"], 
                        name="Stock Price", 
                        line=dict(color="#ff7f0e", width=3)
                    ), secondary_y=True)
                    
                    fig_dual.update_layout(
                        title=f"{m_company}: Sentiment vs Price Sentiment", 
                        hovermode="x unified", height=400,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_dual, width='stretch')

                with col_gauge:
                    signal = corr.get("signal_strength", 0)
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number", value=signal,
                        title={"text": "Signal Strength", "font": {"size": 16}},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "#1f77b4"},
                            "steps": [
                                {"range": [0, 30], "color": "#ff6b6b"},
                                {"range": [30, 60], "color": "#ffd93d"},
                                {"range": [60, 100], "color": "#6bcb77"},
                            ]
                        }
                    ))
                    fig_gauge.update_layout(height=250, margin=dict(t=40, b=0, l=10, r=10))
                    st.plotly_chart(fig_gauge, width='stretch')
            
            # Lag Analysis Table
            lag_data = corr.get("lag_analysis", [])
            if lag_data:
                st.subheader("Lag Correlation Analysis", help="Measures if sentiment changes lead to price changes.")
                df_lag = pd.DataFrame(lag_data)
                df_lag["lag"] = df_lag["lag"].apply(lambda x: f"{x} day{'s' if x != 1 else ''}")
                st.dataframe(df_lag, width='stretch', hide_index=True)

            if st.button("📄 Export Correlation PDF", key="exp_corr"):
                pdf_bytes = get_pdf_bytes("Market Correlation Report", [corr])
                st.download_button("Download Correlation PDF", data=pdf_bytes, file_name=f"correlation_{m_company}.pdf")

    # 3. Intelligence Feed (Strict filtering)
    st.divider()
    st.subheader("📰 Entity Intelligence Feed")
    try:
        # Use st.session_state["selected_entity"] for filtering
        df_feed = get_dashboard_data(st.session_state["selected_entity"], source_filter, cat_filter, "COMPANY", campaign_filter, sent_range)
        if df_feed.empty:
            st.info(f"No recent intelligence events found for {st.session_state['selected_entity']}.")
        else:
            st.dataframe(df_feed, width='stretch')
            if st.button("Generate Feed Report (PDF)"):
                pdf_bytes = get_pdf_bytes(f"{st.session_state['selected_entity']} Intel Report", df_feed.head(20).to_dict('records'))
                st.download_button("Download PDF", data=pdf_bytes, file_name=f"intel_{st.session_state['selected_entity']}.pdf")
    except Exception as e:
        st.error(f"Feed error: {e}")

elif st.session_state["view_mode"] == "People":
    st.header(f"👤 People Watch: {st.session_state['selected_entity']}")
    try:
        df_people = get_dashboard_data(st.session_state["selected_entity"], source_filter, cat_filter, "USER", campaign_filter, sent_range)
        if df_people.empty:
            st.info(f"No data found for {st.session_state['selected_entity']}.")
        else:
            st.subheader("Intelligence Feed")
            st.dataframe(df_people, width='stretch')
    except Exception as e:
        st.error(f"People view error: {e}")

elif st.session_state["view_mode"] == "Graph":
    st.header("🕸️ Knowledge Graph")
    st.caption("Interactive network of entities discovered from intelligence feeds.")
    
    # Graph Controls
    col_g1, col_g2, col_g3 = st.columns([1, 1, 2])
    with col_g1:
        kg_entity = st.text_input("Central Entity (Optional)", value=st.session_state["selected_entity"] if st.session_state["selected_entity"] != "All" else "", help="Leave blank to see the whole network")
    with col_g2:
        kg_min_co = st.number_input("Min Co-mentions", min_value=1, value=2, help="Filter out weak relationships")
    with col_g3:
        kg_types = st.multiselect("Entity Types", ["COMPANY", "PERSON", "ORG", "TOPIC", "PRODUCT", "LOCATION"], default=["COMPANY", "PERSON", "ORG", "TOPIC"])
    
    # Fetch Graph Data
    try:
        with st.spinner("Building Graph..."):
            params = {
                "min_co_occurrences": kg_min_co,
                "days": 30, # Could make this a control
            }
            if kg_entity:
                params["entity"] = kg_entity
            if kg_types:
                params["entity_types"] = ",".join(kg_types)
                
            res = requests.get(f"{API_BASE}/knowledge-graph", params=params)
            res.raise_for_status()
            kg_data = res.json()
            
            nodes = kg_data.get("nodes", [])
            edges = kg_data.get("edges", [])
            stats = kg_data.get("stats", {})
            
            # Stats Banner
            c_s1, c_s2, c_s3 = st.columns(3)
            c_s1.metric("Total Entities", stats.get("total_nodes", 0))
            c_s2.metric("Relationships", stats.get("total_edges", 0))
            c_s3.metric("Most Connected", stats.get("most_connected", "None"))
            
            st.divider()
            
            if not nodes:
                st.info("No connections found matching filters.")
            else:
                col_viz, col_detail = st.columns([3, 1])
                
                with col_viz:
                    # Build pyvis graph
                    from pyvis.network import Network
                    import tempfile
                    
                    # Premium Color Palette
                    color_map = {
                        "COMPANY": "#00d2ff", # Cyan
                        "PERSON": "#00ff87",  # Spring Green
                        "ORG": "#ff9a3b",     # Orange
                        "TOPIC": "#bc6ff1",    # Purple
                        "PRODUCT": "#ff4b2b",  # Red-Orange
                        "LOCATION": "#8d5524"  # Brown
                    }
                    
                    net = Network(height="600px", width="100%", bgcolor="#0E1117", font_color="white", select_menu=False)
                    
                    # Advanced Styling Options
                    options = {
                        "nodes": {
                            "font": {"size": 14, "color": "#ffffff", "face": "Inter"},
                            "shadow": {"enabled": True, "color": "rgba(0,0,0,0.5)"}
                        },
                        "edges": {
                            "smooth": {"type": "continuous", "roundness": 0.5},
                            "color": {"inherit": "both"},
                            "opacity": 0.4,
                            "width": 2
                        },
                        "physics": {
                            "forceAtlas2Based": {
                                "gravitationalConstant": -100,
                                "centralGravity": 0.015,
                                "springLength": 150,
                                "springConstant": 0.05,
                                "avoidOverlap": 1.0
                            },
                            "solver": "forceAtlas2Based",
                            "stabilization": {"iterations": 200}
                        },
                        "interaction": {
                            "hover": True,
                            "tooltipDelay": 100,
                            "hideEdgesOnDrag": True,
                            "zoomView": True
                        }
                    }
                    import json
                    net.set_options(json.dumps(options))
                    
                    # Add nodes
                    for n in nodes:
                        c = color_map.get(n["type"], "#7f7f7f")
                        border_width = 4 if n.get("is_tracked") else 0
                        
                        net.add_node(
                            n["name"], 
                            title=f"Type: {n['type']}\nMentions: {n.get('mention_count')}", 
                            label=n["name"], 
                            value=max(2, n.get("mention_count", 1)) * 3, 
                            color={"background": c, "border": "rgba(255,255,255,0.8)"},
                            borderWidth=border_width
                        )
                    
                    # Add edges
                    for e in edges:
                        s = e.get("avg_sentiment", 0)
                        # More vibrant sentiment colors
                        edge_color = "rgba(0, 255, 135, 0.7)" if s > 0.1 else "rgba(255, 75, 43, 0.7)" if s < -0.1 else "rgba(255, 255, 255, 0.2)"
                        
                        net.add_edge(
                            e["source"], 
                            e["target"], 
                            value=e["weight"],
                            title=f"Co-mentions: {e['weight']}\nAvg Sentiment: {s:.2f}",
                            color=edge_color
                        )
                    
                    html_string = net.generate_html()
                    import re
                    
                    # Fix: Pyvis CDN and Script stabilization
                    html_string = re.sub(
                        r'src="lib/vis-network/vis-network\.min\.js"',
                        'src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"',
                        html_string
                    )
                    html_string = html_string.replace(
                        'https://visjs.github.io/vis-network/standalone/umd/vis-network.min.js',
                        'https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js'
                    )
                    html_string = re.sub(r'<script src="lib/.*"></script>', '', html_string)
                    html_string = re.sub(r'<link rel="stylesheet" href="lib/.*">', '', html_string)

                    import streamlit.components.v1 as components
                    components.html(html_string, height=615, scrolling=False)
                    st.caption("🔵 Company | 🟢 Person | 🟠 Org | 🟣 Topic | 🔴 Product | 🟤 Location. Bold border = Tracked.")
                
                with col_detail:
                    st.subheader("🎯 Entity Deep Dive")
                    all_names = sorted([n["name"] for n in nodes])
                    detail_target = st.selectbox("Select entity from graph", all_names, index=all_names.index(kg_entity) if kg_entity in all_names else 0)
                    
                    if detail_target:
                        det_res = requests.get(f"{API_BASE}/knowledge-graph/entity/{detail_target}/details")
                        if det_res.status_code == 200:
                            det_data = det_res.json()
                            conns = det_data.get("top_connections", [])
                            
                            if conns:
                                # Visualise connections with a chart
                                df_conns = pd.DataFrame(conns)
                                # Map sentiment to colors for plotly
                                df_conns['color'] = df_conns['avg_sentiment'].apply(lambda x: 'Positive' if x > 0.1 else ('Negative' if x < -0.1 else 'Neutral'))
                                
                                fig_conns = px.bar(
                                    df_conns, 
                                    y='name', 
                                    x='co_mentions', 
                                    color='avg_sentiment',
                                    color_continuous_scale="RdYlGn",
                                    range_color=[-1, 1],
                                    orientation='h',
                                    title=f"Top Relationships",
                                    labels={'co_mentions': 'Strength', 'name': '', 'avg_sentiment': 'Sentiment'}
                                )
                                fig_conns.update_layout(
                                    showlegend=False, 
                                    height=400, 
                                    margin=dict(l=150, r=20, t=40, b=40),
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    font_color="white",
                                    yaxis={'categoryorder':'total ascending'}
                                )
                                st.plotly_chart(fig_conns, width='stretch')
                            else:
                                st.info("No strong connections found.")
                                
                            st.divider()
                            st.markdown("🎯 **Track from Graph**")
                            # Form to create a target from this entity
                            with st.form(f"track_{detail_target}"):
                                t_src = st.selectbox("Source", ["Google News", "Reddit Subreddit", "Nitter/X User"])
                                if st.form_submit_button("Start Tracking"):
                                    payload = {
                                        "target_name": detail_target,
                                        "source_type": t_src,
                                        "scrape_interval_minutes": 60,
                                        "campaign": "Discovered via Graph"
                                    }
                                    requests.post(f"{API_BASE}/targets", json=payload)
                                    st.success(f"Added {detail_target}!")

    except Exception as e:
        st.error(f"Failed to load Knowledge Graph: {e}")

# ... End of Dashboard ...
