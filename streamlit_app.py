"""
Manufacturing Schedule Dashboard - MHS Crane Edition
Minimal iOS-Inspired UI with Navy Blue and Gold branding

LOGO INSTRUCTIONS:
To add the real MHS logo, replace line ~160 with your logo image path:
<img src="assets/mhs_logo.png" style="height: 50px; margin-right: 20px;">
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional
import pytz

from data import fetch_schedule_data, write_to_google_sheets, DataSourceConfig, DataFetchError

# Page configuration
st.set_page_config(
    page_title="MHS Manufacturing Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Timezone
TZ = pytz.timezone('America/New_York')

# ============================================================================
# iOS-INSPIRED MINIMAL DESIGN SYSTEM
# ============================================================================

NAVY = "#1a2332"
GOLD = "#d4af37"
BACKGROUND = "#f5f5f7"  # iOS system background
CARD_BG = "#ffffff"
BORDER_LIGHT = "#d2d2d7"  # iOS border color
TEXT_PRIMARY = "#1d1d1f"  # iOS text
TEXT_SECONDARY = "#86868b"  # iOS secondary text
SHADOW_SUBTLE = "0 1px 3px rgba(0,0,0,0.04)"
SHADOW_ELEVATED = "0 2px 8px rgba(0,0,0,0.08)"

st.markdown(f"""
    <style>
    /* iOS System Font Stack */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {{
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', 'Inter', sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }}
    
    /* Global Background */
    .stApp {{
        background: {BACKGROUND};
    }}
    
    .block-container {{
        padding-top: 0.5rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }}
    
    /* Header Bar - iOS Navigation Bar Style */
    .mhs-header {{
        background: {NAVY};
        backdrop-filter: saturate(180%) blur(20px);
        padding: 1rem 2rem;
        border-radius: 0;
        margin: -1rem -1rem 1.5rem -1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 0 rgba(0,0,0,0.1);
    }}
    
    .mhs-logo-placeholder {{
        width: 140px;
        height: 44px;
        background: {GOLD};
        border: 1.5px solid rgba(0,0,0,0.2);
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Arial Black', sans-serif;
        font-size: 22px;
        font-weight: 900;
        color: #000000;
        letter-spacing: 5px;
        margin-right: 14px;
    }}
    
    .mhs-title {{
        color: #ffffff !important;
        font-size: 1.375rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: -0.4px;
    }}
    
    .mhs-datetime {{
        color: rgba(255,255,255,0.65);
        font-size: 0.8125rem;
        font-weight: 400;
        letter-spacing: -0.1px;
    }}
    
    /* KPI Cards - iOS Style */
    .kpi-card {{
        background: {CARD_BG};
        border: 0.5px solid {BORDER_LIGHT};
        border-radius: 10px;
        padding: 1.125rem 1rem;
        text-align: center;
        box-shadow: {SHADOW_SUBTLE};
        transition: all 0.15s ease-out;
    }}
    
    .kpi-card:hover {{
        transform: translateY(-1px);
        box-shadow: {SHADOW_ELEVATED};
    }}
    
    .kpi-label {{
        color: {TEXT_SECONDARY};
        font-size: 0.6875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 0.375rem;
    }}
    
    .kpi-value {{
        color: {TEXT_PRIMARY};
        font-size: 1.875rem;
        font-weight: 700;
        line-height: 1.1;
        letter-spacing: -0.5px;
    }}
    
    .kpi-value-gold {{
        color: {GOLD};
    }}
    
    .kpi-delta {{
        color: {TEXT_SECONDARY};
        font-size: 0.6875rem;
        margin-top: 0.25rem;
        font-weight: 400;
        letter-spacing: -0.1px;
    }}
    
    /* Section Headers - iOS Style */
    .section-header {{
        background: transparent;
        color: {TEXT_PRIMARY};
        padding: 0.5rem 0;
        font-size: 1.0625rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        letter-spacing: -0.3px;
    }}
    
    .section-content {{
        background: {CARD_BG};
        border: 0.5px solid {BORDER_LIGHT};
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: {SHADOW_SUBTLE};
    }}
    
    /* Status Chips - iOS Pill Style */
    .status-chip {{
        display: inline-block;
        padding: 0.1875rem 0.625rem;
        border-radius: 12px;
        font-size: 0.6875rem;
        font-weight: 500;
        letter-spacing: 0.1px;
    }}
    
    .status-planned {{
        background: #f5f5f7;
        color: {TEXT_SECONDARY};
    }}
    
    .status-in-progress {{
        background: {NAVY};
        color: white;
    }}
    
    .status-complete {{
        background: #e5e5ea;
        color: #48484a;
    }}
    
    .status-hold {{
        background: {GOLD};
        color: {NAVY};
    }}
    
    /* Table - Minimal Borders */
    .stDataFrame {{
        border-radius: 10px;
        border: 0.5px solid {BORDER_LIGHT};
        overflow: hidden;
        box-shadow: {SHADOW_SUBTLE};
    }}
    
    /* Sidebar - Clean */
    [data-testid="stSidebar"] {{
        background: {CARD_BG};
        border-right: 0.5px solid {BORDER_LIGHT};
    }}
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: {TEXT_PRIMARY};
        font-weight: 600;
        font-size: 0.9375rem;
        letter-spacing: -0.2px;
    }}
    
    /* Buttons - iOS System Style */
    .stButton > button {{
        background: {NAVY};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.4375rem 1.125rem;
        font-weight: 500;
        font-size: 0.8125rem;
        letter-spacing: -0.1px;
        transition: all 0.15s ease-out;
        box-shadow: {SHADOW_SUBTLE};
    }}
    
    .stButton > button:hover {{
        background: #2a3542;
        transform: scale(1.01);
    }}
    
    .stButton > button:active {{
        transform: scale(0.98);
    }}
    
    /* Input Fields - iOS Style */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stMultiSelect > div > div,
    .stDateInput > div > div > input {{
        border: 0.5px solid {BORDER_LIGHT};
        border-radius: 8px;
        font-size: 0.8125rem;
        background: {CARD_BG};
        padding: 0.5rem 0.75rem;
        transition: all 0.15s ease-out;
    }}
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {{
        border-color: {NAVY};
        box-shadow: 0 0 0 3px rgba(26, 35, 50, 0.1);
    }}
    
    /* Metrics Override */
    [data-testid="stMetric"] {{
        background: transparent;
    }}
    
    [data-testid="stMetricValue"] {{
        color: {TEXT_PRIMARY};
        font-size: 1.875rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }}
    
    [data-testid="stMetricLabel"] {{
        color: {TEXT_SECONDARY};
        font-size: 0.6875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    
    /* Remove Streamlit Branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* Typography Polish */
    h1, h2, h3, h4, h5, h6 {{
        color: {TEXT_PRIMARY};
        font-weight: 600;
        letter-spacing: -0.4px;
    }}
    
    p {{
        color: {TEXT_PRIMARY};
        letter-spacing: -0.1px;
    }}
    
    /* Dividers - Hairline */
    hr {{
        border: none;
        border-top: 0.5px solid {BORDER_LIGHT};
        margin: 1.5rem 0;
    }}
    </style>
""", unsafe_allow_html=True)


def render_header():
    """Render iOS-style navigation bar header"""
    current_time = datetime.now(TZ).strftime("%B %d, %Y • %I:%M %p")
    
    st.markdown(f"""
        <div class="mhs-header">
            <div style="display: flex; align-items: center;">
                <div class="mhs-logo-placeholder">MHS</div>
                <h1 class="mhs-title">Manufacturing Schedule</h1>
            </div>
            <div class="mhs-datetime">{current_time}</div>
        </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(df: pd.DataFrame) -> None:
    """Render iOS-style KPI cards"""
    today = datetime.now(TZ).date()
    week_end = today + timedelta(days=7)
    
    # Calculate KPIs
    total_jobs = len(df)
    in_progress = len(df[df['Status'] == 'In-Progress']) if 'Status' in df.columns else 0
    
    if 'DueDate' in df.columns and 'Status' in df.columns:
        due_this_week_mask = (
            (df['DueDate'].notna()) & 
            (df['DueDate'].dt.date <= week_end) & 
            (df['DueDate'].dt.date >= today) &
            (df['Status'] != 'Complete')
        )
        due_this_week = due_this_week_mask.sum()
    else:
        due_this_week = 0
    
    overdue = len(df[df['DaysLate'] > 0]) if 'DaysLate' in df.columns else 0
    
    if 'Status' in df.columns and 'DurationDays' in df.columns:
        completed = df[df['Status'] == 'Complete'].copy()
        avg_lead_time = completed['DurationDays'].mean() if len(completed) > 0 else 0
    else:
        avg_lead_time = 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Total Jobs</div>
                <div class="kpi-value">{total_jobs}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">In Progress</div>
                <div class="kpi-value">{in_progress}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        delta_text = f"{due_this_week} jobs" if due_this_week > 0 else "None"
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Due This Week</div>
                <div class="kpi-value">{due_this_week}</div>
                <div class="kpi-delta">{delta_text}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Overdue</div>
                <div class="kpi-value kpi-value-gold">{overdue}</div>
                <div class="kpi-delta">{"⚠️ Attention" if overdue > 0 else "✓ On Track"}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Avg Lead Time</div>
                <div class="kpi-value">{avg_lead_time:.1f}</div>
                <div class="kpi-delta">days</div>
            </div>
        """, unsafe_allow_html=True)


def render_gantt_chart(df: pd.DataFrame) -> None:
    """Render minimal Gantt chart"""
    st.markdown('<div class="section-header">📅 Production Timeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content">', unsafe_allow_html=True)
    
    if df.empty:
        st.warning("No data available for timeline visualization.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    if 'StartDate' not in df.columns or 'CustomerRequestDate' not in df.columns:
        st.info("StartDate and Customer Request Date columns are required for timeline view.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    gantt_df = df[(df['StartDate'].notna()) & (df['CustomerRequestDate'].notna())].copy()
    
    if gantt_df.empty:
        st.info("No jobs with valid dates for timeline view.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    y_axis = 'Branch' if 'Branch' in gantt_df.columns else 'JobID'
    color_by = 'Status' if 'Status' in gantt_df.columns else None
    
    hover_cols = [col for col in ['JobID', 'JobName', 'CustomerName', 'Quantity', 'Priority'] 
                  if col in gantt_df.columns]
    
    fig = px.timeline(
        gantt_df,
        x_start='StartDate',
        x_end='CustomerRequestDate',
        y=y_axis,
        color=color_by,
        hover_data=hover_cols if hover_cols else None,
        color_discrete_map={
            'Planned': '#98989d',
            'In-Progress': NAVY,
            'Complete': '#d1d1d6',
            'Hold': GOLD
        } if color_by else None
    )
    
    today = datetime.now(TZ)
    fig.add_vline(
        x=today.timestamp() * 1000,
        line_dash="dash",
        line_color=GOLD,
        line_width=1.5,
        annotation_text="Today",
        annotation_position="top"
    )
    
    fig.update_layout(
        height=500,
        xaxis_title="Timeline",
        yaxis_title=y_axis,
        showlegend=True,
        hovermode='closest',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="-apple-system, BlinkMacSystemFont, sans-serif", size=11, color=TEXT_PRIMARY),
        legend=dict(
            bgcolor=CARD_BG,
            bordercolor=BORDER_LIGHT,
            borderwidth=0.5
        ),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    fig.update_yaxes(categoryorder='category ascending')
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_editable_table(df: pd.DataFrame, config: DataSourceConfig) -> pd.DataFrame:
    """Render minimal editable table"""
    st.markdown('<div class="section-header">📋 Job Management Console</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content">', unsafe_allow_html=True)
    
    if df.empty:
        st.info("No jobs match the current filters.")
        st.markdown('</div>', unsafe_allow_html=True)
        return df
    
    if config.source_type != 'service_account':
        st.warning("⚠️ Read-only mode: Service Account required for editing.")
    
    display_df = df.copy()
    
    date_cols = ['StartDate', 'CustomerRequestDate', 'ShipDate', 'DueDate']
    for col in date_cols:
        if col in display_df.columns and pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')
    
    preferred_cols = [
        'JobID', 'JobName', 'Branch', 'CustomerName', 'Priority', 
        'Status', 'Quantity', 'StartDate', 'CustomerRequestDate', 'ShipDate', 'DueDate', 'Notes'
    ]
    display_cols = [col for col in preferred_cols if col in display_df.columns]
    
    if not display_cols:
        display_cols = list(display_df.columns)
    
    edited_df = st.data_editor(
        display_df[display_cols],
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "JobID": st.column_config.TextColumn("MHS Job #"),
            "Branch": st.column_config.TextColumn("Branch"),
            "CustomerName": st.column_config.TextColumn("Customer Name"),
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["Planned", "In-Progress", "Complete", "Hold"],
                required=True,
            ),
            "Priority": st.column_config.SelectboxColumn(
                "Priority",
                options=["Low", "Medium", "High", "Critical"],
                required=True,
            ),
            "StartDate": st.column_config.TextColumn("Start Date", help="YYYY-MM-DD"),
            "CustomerRequestDate": st.column_config.TextColumn("Customer Request Date", help="YYYY-MM-DD"),
            "ShipDate": st.column_config.TextColumn("Ship Date", help="YYYY-MM-DD"),
            "DueDate": st.column_config.TextColumn("Due Date", help="YYYY-MM-DD"),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=0, step=1),
        }
    )
    
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("💾 Save Changes", type="primary", disabled=(config.source_type != 'service_account')):
            if config.source_type == 'service_account':
                try:
                    success = write_to_google_sheets(
                        config.spreadsheet_id,
                        config.worksheet_name,
                        edited_df
                    )
                    if success:
                        st.success("✅ Changes saved!")
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col2:
        if st.button("🔄 Discard"):
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    return edited_df


def render_add_job_form(config: DataSourceConfig, df: pd.DataFrame):
    """Render minimal add job form"""
    st.markdown('<div class="section-header">➕ Add New Job</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-content">', unsafe_allow_html=True)
    
    if config.source_type != 'service_account':
        st.warning("⚠️ Service Account required for adding jobs.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    with st.form("add_job_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            job_id = st.text_input("MHS Job #*", placeholder="e.g., MHS-001")
            job_name = st.text_input("Job Name", placeholder="e.g., Widget Assembly")
            branch = st.text_input("Branch", value="Unassigned")
            customer_name = st.text_input("Customer Name", value="Unassigned")
            
        with col2:
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"], index=1)
            status = st.selectbox("Status", ["Planned", "In-Progress", "Complete", "Hold"])
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        
        col3, col4, col5, col6 = st.columns(4)
        with col3:
            start_date = st.date_input("Start Date")
        with col4:
            customer_request_date = st.date_input("Customer Request Date")
        with col5:
            ship_date = st.date_input("Ship Date")
        with col6:
            due_date = st.date_input("Due Date")
        
        notes = st.text_area("Notes", placeholder="Additional information...")
        
        submitted = st.form_submit_button("Add Job", type="primary")
        
        if submitted:
            if not job_id:
                st.error("MHS Job # is required!")
            else:
                new_row = {
                    'JobID': job_id,
                    'JobName': job_name,
                    'Branch': branch,
                    'CustomerName': customer_name,
                    'Priority': priority,
                    'Status': status,
                    'Quantity': quantity,
                    'StartDate': start_date.strftime('%Y-%m-%d'),
                    'CustomerRequestDate': customer_request_date.strftime('%Y-%m-%d'),
                    'ShipDate': ship_date.strftime('%Y-%m-%d'),
                    'DueDate': due_date.strftime('%Y-%m-%d'),
                    'Notes': notes
                }
                
                new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                try:
                    success = write_to_google_sheets(
                        config.spreadsheet_id, config.worksheet_name, new_df
                    )
                    if success:
                        st.success(f"✅ Job {job_id} added!")
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filters"""
    st.sidebar.markdown(f'<h2 style="color: {TEXT_PRIMARY}; font-size: 0.9375rem; font-weight: 600;">⚙️ Filters</h2>', unsafe_allow_html=True)
    
    filtered_df = df.copy()
    
    if 'StartDate' in df.columns and df['StartDate'].notna().any():
        min_date = df['StartDate'].min().date()
        max_date = df['StartDate'].max().date()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start, end = date_range
            filtered_df = filtered_df[
                (filtered_df['StartDate'].dt.date >= start) &
                (filtered_df['StartDate'].dt.date <= end)
            ]
    
    if 'Status' in df.columns:
        statuses = df['Status'].unique().tolist()
        selected_statuses = st.sidebar.multiselect(
            "Status", options=statuses, default=statuses
        )
        filtered_df = filtered_df[filtered_df['Status'].isin(selected_statuses)]
    
    if 'Branch' in df.columns:
        branches = ['All'] + sorted(df['Branch'].unique().tolist())
        selected_branch = st.sidebar.selectbox("Branch", options=branches)
        if selected_branch != 'All':
            filtered_df = filtered_df[filtered_df['Branch'] == selected_branch]
    
    if 'CustomerName' in df.columns:
        customers = ['All'] + sorted(df['CustomerName'].unique().tolist())
        selected_customer = st.sidebar.selectbox("Customer Name", options=customers)
        if selected_customer != 'All':
            filtered_df = filtered_df[filtered_df['CustomerName'] == selected_customer]
    
    if 'Priority' in df.columns:
        priorities = ['All'] + sorted(df['Priority'].unique().tolist())
        selected_priority = st.sidebar.selectbox("Priority", options=priorities)
        if selected_priority != 'All':
            filtered_df = filtered_df[filtered_df['Priority'] == selected_priority]
    
    search_term = st.sidebar.text_input("🔍 Search")
    if search_term:
        search_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in ['JobID', 'JobName', 'Notes']:
            if col in filtered_df.columns:
                search_mask |= filtered_df[col].astype(str).str.contains(
                    search_term, case=False, na=False
                )
        filtered_df = filtered_df[search_mask]
    
    st.sidebar.markdown("---")
    st.sidebar.metric("Filtered Jobs", len(filtered_df))
    
    return filtered_df


def main():
    """Main application"""
    render_header()
    
    st.sidebar.markdown(f'<h2 style="color: {TEXT_PRIMARY}; font-size: 0.9375rem; font-weight: 600;">📡 Data Source</h2>', unsafe_allow_html=True)
    
    data_source = st.sidebar.radio(
        "Connection Type",
        options=["Service Account", "Public CSV"],
        help="Service Account required for editing"
    )
    
    if data_source == "Service Account":
        config = DataSourceConfig(
            source_type='service_account',
            spreadsheet_id='1VzMAtlzb58NTsCoGXpsBpp1qrGrZab8lnQqFxSgS7yk',
            worksheet_name=st.sidebar.text_input(
                "Worksheet Name", 
                value="Job Status"
            )
        )
    else:
        csv_url = st.sidebar.text_input("Published CSV URL")
        config = DataSourceConfig(source_type='public_csv', csv_url=csv_url)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    try:
        df, last_refresh = fetch_schedule_data(config)
        
        if last_refresh:
            st.sidebar.success(f"🕒 {last_refresh.strftime('%I:%M %p')}")
        
        if df.empty:
            st.warning("No data found. Check configuration.")
            return
        
        with st.sidebar.expander("📋 Columns"):
            st.write(list(df.columns))
        
        filtered_df = apply_filters(df)
        
        if not filtered_df.empty:
            csv = filtered_df.to_csv(index=False)
            st.sidebar.download_button(
                "📥 Export CSV",
                data=csv,
                file_name=f"mhs_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        render_kpi_cards(filtered_df)
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        render_gantt_chart(filtered_df)
        render_editable_table(filtered_df, config)
        render_add_job_form(config, df)
        
    except DataFetchError as e:
        st.error(f"❌ {str(e)}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()