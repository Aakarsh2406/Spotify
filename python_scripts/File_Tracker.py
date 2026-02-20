import ast
import logging
import calendar
import shutil
import re
import datetime
import pathlib
import pandas as pd
import os
import argparse

from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from file_download import get_file_Quality_Files_Info
# from Scripts.Utilities.alerts_utility import send_alert
# from Scripts.Utilities import central_logger
from Scripts.Utilities import database_connection_utilities as db_connection, central_logger
from Scripts.Utilities.database_connection_utilities import establish_snowflake_conn_sqlalchemy, establish_snowflake_conn_key_pair
from Scripts.SFTP.file_upload import move_file_to_sftp
from Scripts.SFTP.delivery_logging import track_supplemental_files
from Scripts.SFTP.spacex import get_tasks, get_task_steps, get_partner_info, update_next_run_date
from snowflake.connector.pandas_tools import write_pandas
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Activate central logger
central_logger.activate_file_handler('attribution_files_checker.log')
logger = central_logger.primary_logger

# MISSED_FILES = []
# FILES_FOUND = []

def get_task_metadata(task_id, environment):
    """
    Reads the Data Dictionary and prefixes the Base Table based on environment.
    Example: 'DB.SCHEMA.TABLE' -> 'DB_DEV.SCHEMA.TABLE'
    """
    file_path = Path(r"P:\PriviaDataWarehouse\testing\Attribution_Data_Dictionary.xlsx")
    
    try:
        df = pd.read_excel(file_path)
        task_info = df[df['TaskID'] == task_id]
        
        if not task_info.empty:
            base_table = task_info['Base Table Name'].iloc[0] 
            expected_pattern = task_info['Expected Dynamic Pattern'].iloc[0]
            sourcefilename = task_info['SourceFileName'].iloc[0]
            
            # --- Dynamic Database Logic ---
            parts = base_table.split('.')
            db_name = parts[0]
            
            if environment.lower() == 'dev':
                parts[0] = f"{db_name}_DEV"
            elif environment.lower() == 'qa':
                parts[0] = f"{db_name}_QA"
            # Prod stays as is: parts[0] = db_name
            
            final_table_name = ".".join(parts)
            
            return task_id, final_table_name, expected_pattern, sourcefilename
        else:
            return None, None, None, None
            
    except Exception as e:
        logger.error(f"Error reading metadata: {e}")
        return None, None, None, None

# --- Example Usage ---
# file_path = 'Attribution_Data_Dictionary.xlsx'
# tid, table, pattern = get_task_metadata(file_path, 6066)
# print(f"Task: {tid}, Table: {table}, Pattern: {pattern}")


def get_latest_source_date(cursor, table_name, file_name):
    """
    Returns the latest sourcefiledate for a specific file from Snowflake using cursor.
    """
    query = f"SELECT MAX(sourcefiledate) FROM {table_name} WHERE sourcefilename = %s"
    
    try:
        cursor.execute(query, (file_name,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return result[0] 
        return None
        
    except Exception as e:
        logger.error(f"Error fetching date from {table_name}: {e}")
        return None

def get_monthly_intervals(source_file_date):
    """
    Returns a list of YYYY-MM strings. 
    Ensures both inputs are cast to .date() to avoid TypeError.
    """
    if not source_file_date:
        return []

    # Ensure the input is converted to a date object if it's a datetime
    if hasattr(source_file_date, 'date'):
        source_file_date = source_file_date.date()

    intervals = []
    current_step = source_file_date + relativedelta(months=1)
    
    # Standardize 'today' as a date object
    today = datetime.now().date()

    # Now both are date objects, comparison will succeed
    while current_step <= today:
        intervals.append(current_step.strftime('%Y-%m'))
        current_step += relativedelta(months=1)
        
    return intervals

def format_interval_for_pattern_old(interval_str, pattern):
    """
    Detects if the pattern uses 'YYYYMM', 'YYYY/MM', or 'YYYY-MM' 
    and formats the interval string (e.g., '2025-12') accordingly.
    """
    # Use Regex to find the date placeholder (YYYY and MM with any separator)
    match = re.search(r'YYYY(.)?MM', pattern, re.IGNORECASE)
    
    if match:
        placeholder = match.group(0) # e.g., 'YYYY/MM'
        separator = match.group(1) if match.group(1) else "" # e.g., '/'
        
        # Split our standard '2025-12' to get year and month
        year, month = interval_str.split('-')
        
        # Reconstruct based on the detected separator
        formatted_date = f"{year}{separator}{month}"
        
        # Replace the placeholder in the original pattern
        return pattern.replace(placeholder, formatted_date)
    
    return pattern


def format_interval_for_pattern(interval_str, pattern):
    """
    Detects YYYY, MM, and DD in patterns and replaces them.
    DD is replaced with a wildcard '*' to match any day of the month.
    """
    if not pattern:
        return pattern

    # 1. Split our standard '2026-02' to get year and month
    year, month = interval_str.split('-')
    
    # 2. Define our replacement map
    # We replace DD with '*' because we are searching for monthly intervals
    replacements = {
        'YYYY': year,
        'MM': month,
        'DD': '*'
    }

    # 3. Use Case-Insensitive Regex to replace placeholders
    # This handles YYYY-DD-MM, YYYY_DD_MM, YYYYMMDD, etc.
    formatted_pattern = pattern
    for placeholder, value in replacements.items():
        # Re-compile regex for each placeholder (case insensitive)
        reg = re.compile(re.escape(placeholder), re.IGNORECASE)
        formatted_pattern = reg.sub(value, formatted_pattern)
    
    return formatted_pattern


def run_sftp_step_old(StepID, SourceLocation, TargetLocation, ArchiveLocation, FileNamingPattern, TaskID, SFTPCommand, SERVERNAME, SERVERPORT, DATAPARTNERID):
    """
    Executes a single SFTP step for a given task.
    """
    logger.info(f"Running SFTP step: TaskID: {TaskID}, StepID: {StepID}")
    sftp_servername, sftp_username, sftp_password = get_partner_info(DATAPARTNERID)
    sftp_port = SERVERPORT
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    part = FileNamingPattern.split('.')
    PayerName = ''
    fresh_pattern = ''

    if FileNamingPattern == 'OH_Privia_Eligibility_*.txt':
        fresh_pattern = part[0].replace('*', '') + (f'{current_year}{current_month:02}')
        print('Fresh Pattern Generated:', fresh_pattern)
        PayerName = 'Ohio'

    if len(fresh_pattern) > 1:
        if SFTPCommand == 'get':
            logger.info(f"Getting file from SFTP: {SourceLocation} to {TargetLocation}...")
            files_with_metadata = get_file_Quality_Files_Info(SourceLocation, TargetLocation, ArchiveLocation, fresh_pattern, sftp_username, sftp_password, sftp_servername, sftp_port)

            result = [(TaskID, file_meta.get('filename')) for file_meta in files_with_metadata if isinstance(file_meta, dict) and file_meta.get('filename')]
            print('Processing Results:', result)
            return 'Success'
    else: 
        logger.info(f"Pattern mismatch for TaskID {TaskID}: {fresh_pattern}")
        return 'Fail'


def run_sftp_step_with_intervals(StepID, SourceLocation, TargetLocation, ArchiveLocation, TaskID, SFTPCommand, SERVERPORT, DATAPARTNERID, basetablename, expectedpattern, intervals):
    """
    Iterates through monthly intervals with flexible pattern replacement.
    """
    logger.info(f"Starting dynamic interval search for TaskID: {TaskID}")
    sftp_servername, sftp_username, sftp_password = get_partner_info(DATAPARTNERID)
    interval_report = []

    for period in intervals:
        # Dynamically determine if we need '202512' or '2025/12'
        fresh_pattern = format_interval_for_pattern(period, expectedpattern)
        
        logger.info(f"Interval: {period} | Applied Pattern: {fresh_pattern}")

        print(f"Interval: {period} | Applied Pattern: {fresh_pattern}")

        if SFTPCommand == 'get':
            files_found = get_file_Quality_Files_Info(
                SourceLocation, TargetLocation, ArchiveLocation, 
                fresh_pattern, sftp_username, sftp_password, 
                sftp_servername, SERVERPORT
            )

            status = "Found" if files_found else "Missing"
            filenames = [f.get('filename') for f in files_found] if files_found else []
            
            interval_report.append({
                'TaskID': TaskID,
                'Interval': period,
                'Status': status,
                'FilesCount': len(filenames),
                'Files': ", ".join(filenames) if filenames else "N/A"
            })

    return pd.DataFrame(interval_report)


def argument_parser(custom_arguments=None):
    parser = argparse.ArgumentParser(
        description="Define Which ENV You  working"
        , epilog="CignaHealthspring load process loads data based on the specified inputs from cmd line."
        , formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-env"
        , choices=["dev","qa","prod"]
        , dest='environment'
        , help=""
        , default=None
    )
    return parser.parse_args(custom_arguments)

def argument_parser(custom_arguments=None):
    parser = argparse.ArgumentParser(
        description="ETL Environment Selector",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Set required=True to make it mandatory
    parser.add_argument(
        "-env", "-e",
        choices=["dev", "qa", "prod"],
        dest='env', 
        required=True, # This forces the user to provide -env
        help="Specify the working environment (dev, qa, or prod)"
    )
    
    return parser.parse_args(custom_arguments)

def main():
    #Get Args Value
    args = argument_parser()
    current_env = args.env
    # Hardcoded Path for the final report
    REPORT_DROP_PATH = r"P:\PriviaDataWarehouse\testing\Reports\Attribution_Audits"
    
    # List to collect results from every task
    master_report_list = []
    
    # Your list of Task IDs to check
    task_list = [6066] # Add all your tasks here

    db_conn = None
    try:
        # Create folder if it doesn't exist
        if not os.path.exists(REPORT_DROP_PATH):
            os.makedirs(REPORT_DROP_PATH)
            
        db_conn = establish_snowflake_conn_key_pair()
        cursor = db_conn.cursor()

        for tid in task_list:
            # Unpack Metadata from Excel
            taskid, basetablename, expectedpattern, sourcefilename = get_task_metadata(tid,current_env)

            if not taskid:
                logger.warning(f"Metadata not found for Task {tid}. Skipping.")
                continue

            # 1. Get the latest date from Snowflake
            last_date = get_latest_source_date(cursor, basetablename, sourcefilename)
            
            if last_date:
                # 2. Get missing monthly intervals
                intervals = get_monthly_intervals(last_date)
                
                # 3. Get SFTP steps
                steps = get_task_steps(taskid)

                for step in steps:
                    # Only run for 'get' commands
                    if step[5].lower() == 'get':
                        # Run the search with the "Stop after Found" logic
                        task_df = run_sftp_step_with_intervals(
                            step[0], step[1], step[2], step[3], taskid, 
                            step[5], step[7], step[8], basetablename, expectedpattern, intervals
                        )

                        if not task_df.empty:
                            # Attach source info for the master report
                            task_df['Base_Table'] = basetablename
                            task_df['Source_File'] = sourcefilename
                            master_report_list.append(task_df)
                            
        # --- EXPORT TO HARDCODED PATH ---
        if master_report_list:
            final_master_df = pd.concat(master_report_list, ignore_index=True)
            
            # Create a clean filename: Attribution_Master_Report_20260220.csv
            file_date = datetime.now().strftime('%Y%m%d')
            final_filename = f"Attribution_Master_Report_{file_date}.csv"
            final_path = os.path.join(REPORT_DROP_PATH, final_filename)
            
            # Save the file
            final_master_df.to_csv(final_path, index=False)
            
            logger.info(f"SUCCESS: Master report exported to {final_path}")
            print(f"\n[FINAL REPORT GENERATED]: {final_path}")
        else:
            logger.info("No missing intervals found; no report generated.")

    except Exception as e:
        logger.error(f"CRITICAL ERROR: {str(e)}", exc_info=True)
    finally:
        if db_conn:
            cursor.close()
            db_conn.close()
            logger.info("Connections closed.")

if __name__ == "__main__":
    main()