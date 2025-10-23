"""
Manufacturing Schedule Dashboard
Main Streamlit application for visualizing and managing manufacturing schedules.
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
    page_title="Manufacturing Schedule Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .status-planned {
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .status-in-progress {
        background-color: #fff3e0;
        color: #f57c00;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .status-complete {
        background-color: #e8f5e9;
        color: #388e3c;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .status-hold {
        background-color: #ffebee;
        color: #d32f2f;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .overdue-row {
        background-color: #ffebee !important;
    }
    </style>
""", unsafe_allow_html=True)

# Timezone
TZ = pytz.timezone('America/New_York')

def render_kpi_cards(df: pd.DataFrame) -> None:
    """Render KPI metric cards at the top of the dashboard."""
    today = datetime.now(TZ).date()
    week_end = today + timedelta(days=7)
    
    # Calculate KPIs
    total_jobs = len(df)
    in_progress = len(df[df['Status'] == 'In-Progress']) if 'Status' in df.columns else 0
    
    # Due this week
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
    
    # Overdue
    overdue = len(df[df['DaysLate'] > 0]) if 'DaysLate' in df.columns else 0
    
    # Average lead time (for completed jobs)
    if 'Status' in df.columns and 'DurationDays' in df.columns:
        completed = df[df['Status'] == 'Complete'].copy()
        if len(completed) > 0:
            avg_lead_time = completed['DurationDays'].mean()
        else:
            avg_lead_time = 0
    else:
        avg_lead_time = 0
    
    # Display in columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Jobs", total_jobs)
    with col2:
        st.metric("In Progress", in_progress)
    with col3:
        st.metric("Due This Week", due_this_week, 
                  delta=None if due_this_week == 0 else f"{due_this_week} jobs")
    with col4:
        st.metric("Overdue", overdue, 
                  delta=f"-{overdue}" if overdue > 0 else "0",
                  delta_color="inverse")
    with col5:
        st.metric("Avg Lead Time", f"{avg_lead_time:.1f} days")


def render_gantt_chart(df: pd.DataFrame) -> None:
    """Render interactive Gantt chart/timeline."""
    if df.empty:
        st.warning("No data available for Gantt chart.")
        return
    
    # Check required columns
    if 'StartDate' not in df.columns or 'EndDate' not in df.columns:
        st.info("StartDate and EndDate columns are required for timeline view.")
        return
    
    # Prepare data for Gantt
    gantt_df = df[
        (df['StartDate'].notna()) & 
        (df['EndDate'].notna())
    ].copy()
    
    if gantt_df.empty:
        st.info("No jobs with valid start and end dates for timeline view.")
        return
    
    # Use WorkCenter if available, otherwise use a default
    y_axis = 'WorkCenter' if 'WorkCenter' in gantt_df.columns else 'JobID'
    color_by = 'Status' if 'Status' in gantt_df.columns else None
    
    # Prepare hover data
    hover_cols = []
    for col in ['JobID', 'JobName', 'Owner', 'Quantity', 'Priority']:
        if col in gantt_df.columns:
            hover_cols.append(col)
    
    # Create timeline
    fig = px.timeline(
        gantt_df,
        x_start='StartDate',
        x_end='EndDate',
        y=y_axis,
        color=color_by,
        hover_data=hover_cols if hover_cols else None,
        title='Manufacturing Schedule Timeline',
        color_discrete_map={
            'Planned': '#1976d2',
            'In-Progress': '#f57c00',
            'Complete': '#388e3c',
            'Hold': '#d32f2f'
        } if color_by else None
    )
    
    # Add today marker
    today = datetime.now(TZ)
    fig.add_vline(
        x=today.timestamp() * 1000,  # Plotly uses milliseconds
        line_dash="dash",
        line_color="red",
        annotation_text="Today",
        annotation_position="top"
    )
    
    # Update layout
    fig.update_layout(
        height=500,
        xaxis_title="Timeline",
        yaxis_title=y_axis,
        showlegend=True,
        hovermode='closest'
    )
    
    fig.update_yaxes(categoryorder='category ascending')
    
    st.plotly_chart(fig, use_container_width=True)


def render_editable_table(df: pd.DataFrame, config: DataSourceConfig) -> pd.DataFrame:
    """Render editable data table with save functionality."""
    st.subheader("📋 Job List (Editable)")
    
    if df.empty:
        st.info("No jobs match the current filters.")
        return df
    
    # Show editing options only for service account mode
    if config.source_type != 'service_account':
        st.warning("⚠️ Editing requires Service Account authentication. Currently in read-only mode (Public CSV).")
    
    # Prepare display dataframe
    display_df = df.copy()
    
    # Format dates for display/editing - keep as strings
    date_cols = ['StartDate', 'EndDate', 'DueDate']
    for col in date_cols:
        if col in display_df.columns and pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime('%Y-%m-%d')
    
    # Select columns to display
    preferred_cols = [
        'JobID', 'JobName', 'WorkCenter', 'Owner', 'Priority', 
        'Status', 'Quantity', 'StartDate', 'EndDate', 'DueDate', 'Notes'
    ]
    display_cols = [col for col in preferred_cols if col in display_df.columns]
    
    if not display_cols:
        display_cols = list(display_df.columns)
    
    # Editable data editor
    edited_df = st.data_editor(
        display_df[display_cols],
        use_container_width=True,
        num_rows="dynamic",  # Allow adding/deleting rows
        hide_index=True,
        column_config={
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
            "StartDate": st.column_config.TextColumn(
                "Start Date",
                help="Format: YYYY-MM-DD",
            ),
            "EndDate": st.column_config.TextColumn(
                "End Date",
                help="Format: YYYY-MM-DD",
            ),
            "DueDate": st.column_config.TextColumn(
                "Due Date",
                help="Format: YYYY-MM-DD",
            ),
            "Quantity": st.column_config.NumberColumn(
                "Quantity",
                min_value=0,
                step=1,
            ),
        }
    )
    
    # Save button
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        if st.button("💾 Save Changes", type="primary", disabled=(config.source_type != 'service_account')):
            if config.source_type == 'service_account':
                try:
                    # Write back to Google Sheets
                    success = write_to_google_sheets(
                        config.spreadsheet_id,
                        config.worksheet_name,
                        edited_df
                    )
                    if success:
                        st.success("✅ Changes saved successfully!")
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving changes: {str(e)}")
            else:
                st.error("Service Account authentication required for editing.")
    
    with col2:
        if st.button("🔄 Discard Changes"):
            st.rerun()
    
    return edited_df


def render_add_job_form(config: DataSourceConfig, df: pd.DataFrame):
    """Render form to add a new job."""
    st.subheader("➕ Add New Job")
    
    if config.source_type != 'service_account':
        st.warning("⚠️ Adding jobs requires Service Account authentication.")
        return
    
    with st.form("add_job_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            job_id = st.text_input("MHS JOB #*", placeholder="e.g., MHS-001")
            job_name = st.text_input("Job Name", placeholder="e.g., Widget Assembly")
            work_center = st.text_input("Work Center", value="Unassigned")
            owner = st.text_input("Owner", value="Unassigned")
            
        with col2:
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"], index=1)
            status = st.selectbox("Status", ["Planned", "In-Progress", "Complete", "Hold"])
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        
        col3, col4, col5 = st.columns(3)
        with col3:
            start_date = st.date_input("Start Date")
        with col4:
            end_date = st.date_input("End Date")
        with col5:
            due_date = st.date_input("Due Date")
        
        notes = st.text_area("Notes", placeholder="Additional information...")
        
        submitted = st.form_submit_button("Add Job", type="primary")
        
        if submitted:
            if not job_id:
                st.error("MHS JOB # is required!")
            else:
                # Create new row
                new_row = {
                    'JobID': job_id,
                    'JobName': job_name,
                    'WorkCenter': work_center,
                    'Owner': owner,
                    'Priority': priority,
                    'Status': status,
                    'Quantity': quantity,
                    'StartDate': start_date.strftime('%Y-%m-%d'),
                    'EndDate': end_date.strftime('%Y-%m-%d'),
                    'DueDate': due_date.strftime('%Y-%m-%d'),
                    'Notes': notes
                }
                
                # Append to dataframe
                new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                try:
                    # Write back to Google Sheets
                    success = write_to_google_sheets(
                        config.spreadsheet_id,
                        config.worksheet_name,
                        new_df
                    )
                    if success:
                        st.success(f"✅ Job {job_id} added successfully!")
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error adding job: {str(e)}")


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filters to dataframe."""
    st.sidebar.header("📊 Filters")
    
    filtered_df = df.copy()
    
    # Date range filter
    if 'StartDate' in df.columns and df['StartDate'].notna().any():
        min_date = df['StartDate'].min().date()
        max_date = df['StartDate'].max().date()
        
        date_range = st.sidebar.date_input(
            "Date Range (Start Date)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Filter jobs by start date range"
        )
        
        if len(date_range) == 2:
            start, end = date_range
            filtered_df = filtered_df[
                (filtered_df['StartDate'].dt.date >= start) &
                (filtered_df['StartDate'].dt.date <= end)
            ]
    
    # Status filter
    if 'Status' in df.columns:
        statuses = df['Status'].unique().tolist()
        selected_statuses = st.sidebar.multiselect(
            "Status",
            options=statuses,
            default=statuses,
            help="Filter by job status"
        )
        filtered_df = filtered_df[filtered_df['Status'].isin(selected_statuses)]
    
    # Work Center filter
    if 'WorkCenter' in df.columns:
        work_centers = ['All'] + sorted(df['WorkCenter'].unique().tolist())
        selected_wc = st.sidebar.selectbox(
            "Work Center",
            options=work_centers,
            help="Filter by work center/resource"
        )
        if selected_wc != 'All':
            filtered_df = filtered_df[filtered_df['WorkCenter'] == selected_wc]
    
    # Owner filter
    if 'Owner' in df.columns:
        owners = ['All'] + sorted(df['Owner'].unique().tolist())
        selected_owner = st.sidebar.selectbox(
            "Owner",
            options=owners,
            help="Filter by job owner"
        )
        if selected_owner != 'All':
            filtered_df = filtered_df[filtered_df['Owner'] == selected_owner]
    
    # Priority filter
    if 'Priority' in df.columns:
        priorities = ['All'] + sorted(df['Priority'].unique().tolist())
        selected_priority = st.sidebar.selectbox(
            "Priority",
            options=priorities,
            help="Filter by priority level"
        )
        if selected_priority != 'All':
            filtered_df = filtered_df[filtered_df['Priority'] == selected_priority]
    
    # Text search
    search_term = st.sidebar.text_input(
        "Search (Job ID, Name, Notes)",
        help="Search in JobID, JobName, and Notes fields"
    )
    if search_term:
        search_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        
        if 'JobID' in filtered_df.columns:
            search_mask |= filtered_df['JobID'].astype(str).str.contains(search_term, case=False, na=False)
        if 'JobName' in filtered_df.columns:
            search_mask |= filtered_df['JobName'].astype(str).str.contains(search_term, case=False, na=False)
        if 'Notes' in filtered_df.columns:
            search_mask |= filtered_df['Notes'].astype(str).str.contains(search_term, case=False, na=False)
        
        filtered_df = filtered_df[search_mask]
    
    st.sidebar.markdown("---")
    st.sidebar.metric("Filtered Jobs", len(filtered_df))
    
    return filtered_df


def main():
    """Main application entry point."""
    st.title("🏭 Manufacturing Schedule Dashboard")
    
    # Sidebar configuration
    st.sidebar.title("⚙️ Configuration")
    
    # Data source selection
    data_source = st.sidebar.radio(
        "Data Source",
        options=["Service Account", "Public CSV"],
        help="Choose how to connect to Google Sheets. Use Service Account for editing."
    )
    
    # Configure data source
    if data_source == "Service Account":
        config = DataSourceConfig(
            source_type='service_account',
            spreadsheet_id='1VzMAtlzb58NTsCoGXpsBpp1qrGrZab8lnQqFxSgS7yk',
            worksheet_name=st.sidebar.text_input(
                "Worksheet Name", 
                value="Job Status",
                help="Name of the worksheet tab to read"
            )
        )
    else:
        csv_url = st.sidebar.text_input(
            "Published CSV URL",
            help="Google Sheets CSV export URL (Read-only mode)"
        )
        config = DataSourceConfig(
            source_type='public_csv',
            csv_url=csv_url if csv_url else None
        )
    
    # Refresh controls
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh Data", help="Clear cache and reload data"):
        st.cache_data.clear()
        st.rerun()
    
    # Fetch data
    try:
        df, last_refresh = fetch_schedule_data(config)
        
        if last_refresh:
            st.sidebar.success(f"Last refresh: {last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if df.empty:
            st.warning("No data found in the sheet. Please check the configuration.")
            return
        
        # Show detected columns
        with st.sidebar.expander("📋 Detected Columns", expanded=False):
            st.write(list(df.columns))
        
        # Apply filters
        filtered_df = apply_filters(df)
        
        # Export button
        if not filtered_df.empty:
            csv = filtered_df.to_csv(index=False)
            st.sidebar.download_button(
                label="📥 Download Filtered Data",
                data=csv,
                file_name=f"manufacturing_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Main dashboard
        st.markdown("---")
        
        # KPI Cards
        render_kpi_cards(filtered_df)
        
        st.markdown("---")
        
        # Gantt Chart
        st.subheader("📅 Schedule Timeline")
        render_gantt_chart(filtered_df)
        
        st.markdown("---")
        
        # Editable Table
        edited_df = render_editable_table(filtered_df, config)
        
        st.markdown("---")
        
        # Add Job Form
        render_add_job_form(config, df)
        
    except DataFetchError as e:
        st.error(f"❌ Error fetching data: {str(e)}")
        st.info("Please check your configuration and credentials in the sidebar.")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()