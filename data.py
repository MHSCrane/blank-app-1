"""
Data fetching and processing utilities for the manufacturing schedule dashboard.
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
import pytz
from dataclasses import dataclass
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone
TZ = pytz.timezone('America/New_York')


class DataFetchError(Exception):
    """Custom exception for data fetching errors."""
    pass


@dataclass
class DataSourceConfig:
    """Configuration for data source."""
    source_type: str  # 'service_account' or 'public_csv'
    spreadsheet_id: Optional[str] = None
    worksheet_name: Optional[str] = None
    csv_url: Optional[str] = None


def get_google_sheets_client() -> gspread.Client:
    """
    Create and return authenticated Google Sheets client using service account.
    
    Returns:
        Authenticated gspread client
        
    Raises:
        DataFetchError: If authentication fails
    """
    try:
        # Get service account credentials from Streamlit secrets
        credentials_dict = st.secrets.get("gcp_service_account")
        
        if not credentials_dict:
            raise DataFetchError(
                "Service account credentials not found in Streamlit secrets. "
                "Please configure [gcp_service_account] in .streamlit/secrets.toml"
            )
        
        # Define the required scopes - UPDATED TO INCLUDE WRITE ACCESS
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',  # Full access for read/write
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Create credentials object
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
        
        # Authorize and return client
        client = gspread.authorize(credentials)
        return client
        
    except Exception as e:
        logger.error(f"Failed to authenticate with Google Sheets: {str(e)}")
        raise DataFetchError(f"Authentication failed: {str(e)}")


def fetch_from_service_account(
    spreadsheet_id: str,
    worksheet_name: str
) -> pd.DataFrame:
    """
    Fetch data from Google Sheets using service account authentication.
    
    Args:
        spreadsheet_id: The Google Sheets spreadsheet ID
        worksheet_name: Name of the worksheet to read
        
    Returns:
        DataFrame containing the sheet data
        
    Raises:
        DataFetchError: If fetching fails
    """
    try:
        client = get_google_sheets_client()
        
        # Open spreadsheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Get worksheet
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            available_sheets = [ws.title for ws in spreadsheet.worksheets()]
            raise DataFetchError(
                f"Worksheet '{worksheet_name}' not found. "
                f"Available worksheets: {', '.join(available_sheets)}"
            )
        
        # Get all values
        data = worksheet.get_all_records()
        
        if not data:
            logger.warning("No data found in worksheet")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        logger.info(f"Successfully fetched {len(df)} rows from Google Sheets")
        return df
        
    except DataFetchError:
        raise
    except Exception as e:
        logger.error(f"Error fetching from Google Sheets: {str(e)}")
        raise DataFetchError(f"Failed to fetch data: {str(e)}")


def write_to_google_sheets(
    spreadsheet_id: str,
    worksheet_name: str,
    df: pd.DataFrame
) -> bool:
    """
    Write dataframe back to Google Sheets.
    
    Args:
        spreadsheet_id: The Google Sheets spreadsheet ID
        worksheet_name: Name of the worksheet to write to
        df: DataFrame to write
        
    Returns:
        True if successful
        
    Raises:
        DataFetchError: If writing fails
    """
    try:
        client = get_google_sheets_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        # Convert dataframe to list of lists
        # Include headers
        values = [df.columns.tolist()] + df.values.tolist()
        
        # Clear existing data and write new data
        worksheet.clear()
        worksheet.update('A1', values)
        
        logger.info(f"Successfully wrote {len(df)} rows to Google Sheets")
        return True
        
    except Exception as e:
        logger.error(f"Error writing to Google Sheets: {str(e)}")
        raise DataFetchError(f"Failed to write data: {str(e)}")


def fetch_from_public_csv(csv_url: str) -> pd.DataFrame:
    """
    Fetch data from a publicly published CSV URL.
    
    Args:
        csv_url: URL to the published CSV
        
    Returns:
        DataFrame containing the CSV data
        
    Raises:
        DataFetchError: If fetching fails
    """
    try:
        if not csv_url:
            raise DataFetchError("CSV URL is required for public CSV mode")
        
        df = pd.read_csv(csv_url)
        logger.info(f"Successfully fetched {len(df)} rows from public CSV")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching from CSV: {str(e)}")
        raise DataFetchError(f"Failed to fetch CSV: {str(e)}")


def infer_date_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Infer which columns contain date information based on column names.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Dictionary mapping standard date field names to actual column names
    """
    date_mapping = {}
    
    # Common patterns for date columns
    patterns = {
        'StartDate': ['start', 'startdate', 'start_date', 'begin', 'begindate'],
        'CustomerRequestDate': ['customerrequest', 'customer_request', 'end', 'enddate', 'end_date', 'finish', 'finishdate'],
        'ShipDate': ['ship', 'shipdate', 'ship_date', 'shipping'],
        'DueDate': ['due', 'duedate', 'due_date', 'deadline']
    }
    
    for col in df.columns:
        col_lower = col.lower().replace(' ', '').replace('#', '')
        for standard_name, keywords in patterns.items():
            if any(keyword in col_lower for keyword in keywords):
                date_mapping[standard_name] = col
                break
    
    return date_mapping


def parse_dates(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Parse date columns and convert to datetime with timezone awareness.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Tuple of (processed DataFrame, list of warnings)
    """
    warnings = []
    date_mapping = infer_date_columns(df)
    
    # Rename columns to standard names
    rename_dict = {v: k for k, v in date_mapping.items()}
    df = df.rename(columns=rename_dict)
    
    # Parse each date column
    for date_col in ['StartDate', 'CustomerRequestDate', 'ShipDate', 'DueDate']:
        if date_col in df.columns:
            try:
                # Try to parse dates
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
                # Count parsing failures
                null_count = df[date_col].isna().sum()
                if null_count > 0:
                    warnings.append(
                        f"Failed to parse {null_count} dates in {date_col}"
                    )
                
                # Localize to timezone
                df[date_col] = df[date_col].dt.tz_localize(TZ, ambiguous='infer', nonexistent='shift_forward')
                
            except Exception as e:
                warnings.append(f"Error parsing {date_col}: {str(e)}")
                logger.warning(f"Error parsing {date_col}: {str(e)}")
    
    return df, warnings


def normalize_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize status column values to standard format.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with normalized Status column
    """
    if 'Status' not in df.columns:
        # Try to find status column
        status_cols = [col for col in df.columns if 'status' in col.lower()]
        if status_cols:
            df = df.rename(columns={status_cols[0]: 'Status'})
        else:
            df['Status'] = 'Unknown'
            return df
    
    # Normalize status values
    status_mapping = {
        'planned': 'Planned',
        'in progress': 'In-Progress',
        'in-progress': 'In-Progress',
        'inprogress': 'In-Progress',
        'complete': 'Complete',
        'completed': 'Complete',
        'done': 'Complete',
        'hold': 'Hold',
        'on hold': 'Hold',
        'paused': 'Hold',
        'pending': 'Planned'
    }
    
    df['Status'] = df['Status'].astype(str).str.strip().str.lower()
    df['Status'] = df['Status'].map(status_mapping).fillna('Planned')
    
    return df


def add_calculated_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add calculated fields like DaysLate and DurationDays.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with additional calculated fields
    """
    today = datetime.now(TZ)
    
    # Calculate DaysLate
    if 'DueDate' in df.columns and 'Status' in df.columns:
        df['DaysLate'] = 0
        overdue_mask = (
            (df['DueDate'].notna()) &
            (df['DueDate'] < today) &
            (df['Status'] != 'Complete')
        )
        df.loc[overdue_mask, 'DaysLate'] = (
            today - df.loc[overdue_mask, 'DueDate']
        ).dt.days
    else:
        df['DaysLate'] = 0
    
    # Calculate DurationDays - using CustomerRequestDate instead of EndDate
    if 'StartDate' in df.columns and 'CustomerRequestDate' in df.columns:
        duration_mask = df['StartDate'].notna() & df['CustomerRequestDate'].notna()
        df.loc[duration_mask, 'DurationDays'] = (
            df.loc[duration_mask, 'CustomerRequestDate'] - df.loc[duration_mask, 'StartDate']
        ).dt.days
    
    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names and ensure required columns exist.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with standardized columns
    """
    # Column mapping for common variations - UPDATED WITH NEW NAMES
    column_mapping = {
        'mhsjob#': 'JobID',
        'mhsjob': 'JobID',
        'mhs job#': 'JobID',
        'mhs job #': 'JobID',
        'jobid': 'JobID',
        'job_id': 'JobID',
        'id': 'JobID',
        'job': 'JobID',
        'job#': 'JobID',
        'job #': 'JobID',
        'jobname': 'JobName',
        'job_name': 'JobName',
        'name': 'JobName',
        'branch': 'Branch',
        'workcenter': 'Branch',
        'work_center': 'Branch',
        'resource': 'Branch',
        'machine': 'Branch',
        'customername': 'CustomerName',
        'customer_name': 'CustomerName',
        'owner': 'CustomerName',
        'assignee': 'CustomerName',
        'assigned_to': 'CustomerName',
        'customerrequestdate': 'CustomerRequestDate',
        'customer_request_date': 'CustomerRequestDate',
        'enddate': 'CustomerRequestDate',
        'end_date': 'CustomerRequestDate',
        'shipdate': 'ShipDate',
        'ship_date': 'ShipDate',
        'priority': 'Priority',
        'quantity': 'Quantity',
        'qty': 'Quantity',
        'notes': 'Notes',
        'comments': 'Notes',
        'description': 'Notes'
    }
    
    # Apply mapping
    rename_dict = {}
    for col in df.columns:
        col_lower = col.lower().replace(' ', '').replace('_', '').replace('#', '')
        if col_lower in column_mapping:
            rename_dict[col] = column_mapping[col_lower]
    
    df = df.rename(columns=rename_dict)
    
    # Ensure required columns exist with defaults
    required_cols = {
        'JobID': lambda: df.index.astype(str),
        'JobName': '',
        'Branch': 'Unassigned',
        'CustomerName': 'Unassigned',
        'Priority': 'Medium',
        'Status': 'Planned',
        'Quantity': 1,
        'ShipDate': '',
        'Notes': ''
    }
    
    for col, default in required_cols.items():
        if col not in df.columns:
            if callable(default):
                df[col] = default()
            else:
                df[col] = default
    
    return df


def process_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Process raw dataframe: standardize columns, parse dates, add calculated fields.
    
    Args:
        df: Raw DataFrame from data source
        
    Returns:
        Tuple of (processed DataFrame, list of warnings)
    """
    warnings = []
    
    if df.empty:
        return df, warnings
    
    # Standardize column names
    df = standardize_columns(df)
    
    # Parse dates
    df, date_warnings = parse_dates(df)
    warnings.extend(date_warnings)
    
    # Normalize status
    df = normalize_status(df)
    
    # Add calculated fields
    df = add_calculated_fields(df)
    
    return df, warnings


@st.cache_data(ttl=60, show_spinner="Loading schedule data...")
def fetch_schedule_data(config: DataSourceConfig) -> Tuple[pd.DataFrame, datetime]:
    """
    Main function to fetch and process schedule data.
    Cached with 60 second TTL for performance.
    
    Args:
        config: Data source configuration
        
    Returns:
        Tuple of (processed DataFrame, last refresh datetime)
        
    Raises:
        DataFetchError: If data fetching fails
    """
    try:
        # Fetch raw data based on source type
        if config.source_type == 'service_account':
            if not config.spreadsheet_id or not config.worksheet_name:
                raise DataFetchError(
                    "Spreadsheet ID and worksheet name are required for service account mode"
                )
            df = fetch_from_service_account(config.spreadsheet_id, config.worksheet_name)
        elif config.source_type == 'public_csv':
            df = fetch_from_public_csv(config.csv_url)
        else:
            raise DataFetchError(f"Unknown source type: {config.source_type}")
        
        # Process the dataframe
        df, warnings = process_dataframe(df)
        
        # Display warnings in Streamlit if any
        if warnings:
            with st.sidebar:
                with st.expander("⚠️ Data Processing Warnings", expanded=False):
                    for warning in warnings:
                        st.warning(warning)
        
        last_refresh = datetime.now(TZ)
        return df, last_refresh
        
    except DataFetchError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in fetch_schedule_data: {str(e)}")
        raise DataFetchError(f"Failed to fetch schedule data: {str(e)}")