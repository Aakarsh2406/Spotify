import pandas as pd
import os
import argparse
import re
from datetime import datetime
from pathlib import Path
from dateutil.relativedelta import relativedelta

# Import your internal modules
from file_download import get_file_Quality_Files_Info
from Scripts.Utilities import central_logger
from Scripts.Utilities.database_connection_utilities import establish_snowflake_conn_key_pair
from Scripts.SFTP.spacex import get_task_steps, get_partner_info

# Initialize Logger
central_logger.activate_file_handler('attribution_files_checker.log')
logger = central_logger.primary_logger

def get_task_metadata_dynamic(row, environment):
    """
    Processes a single Excel row and handles DB prefixing based on environment.
    """
    try:
        task_id = row['TaskID']
        base_table = str(row['Base Table Name'])
        expected_pattern = row['Expected Dynamic Pattern']
        source_filename = row['SourceFileName']
        
        # --- Mandatory Environment Logic ---
        parts = base_table.split('.')
        db_name = parts[0]
        
        if environment.lower() == 'dev':
            parts[0] = f"{db_name}_DEV"
        elif environment.lower() == 'qa':
            parts[0] = f"{db_name}_QA"
        
        final_table_name = ".".join(parts)
        return task_id, final_table_name, expected_pattern, source_filename
    except Exception as e:
        logger.error(f"Error parsing metadata for row: {e}")
        return None, None, None, None

def get_latest_source_date(cursor, table_name, file_name):
    query = f"SELECT MAX(sourcefiledate) FROM {table_name} WHERE sourcefilename = %s"
    try:
        cursor.execute(query, (file_name,))
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
    except Exception as e:
        logger.error(f"Snowflake Error ({table_name}): {e}")
        return None

def get_monthly_intervals(source_file_date):
    if not source_file_date: return []
    if hasattr(source_file_date, 'date'): source_file_date = source_file_date.date()

    intervals = []
    current_step = source_file_date + relativedelta(months=1)
    today = datetime.now().date()

    while current_step <= today:
        intervals.append(current_step.strftime('%Y-%m'))
        current_step += relativedelta(months=1)
    return intervals

def format_interval_for_pattern(interval_str, pattern):
    if not pattern: return pattern
    year, month = interval_str.split('-')
    replacements = {'YYYY': year, 'MM': month, 'DD': '*'}
    
    formatted_pattern = pattern
    for placeholder, value in replacements.items():
        reg = re.compile(re.escape(placeholder), re.IGNORECASE)
        formatted_pattern = reg.sub(value, formatted_pattern)
    return formatted_pattern
def run_sftp_step_with_intervals(task_id, steps, pattern, intervals, sftp_creds, sftp_port):
    """
    Revised logic: Records every interval status (Found or Missing) 
    instead of stopping after the first success.
    """
    interval_report = []
    sftp_srv, sftp_user, sftp_pwd = sftp_creds

    for period in intervals:
        fresh_pattern = format_interval_for_pattern(period, pattern)
        file_found_for_this_month = False
        found_filenames = []
        
        # Check the SFTP for this specific month
        for step in steps:
            if str(step[5]).lower() == 'get':
                files = get_file_Quality_Files_Info(
                    step[1], step[2], step[3], fresh_pattern, 
                    sftp_user, sftp_pwd, sftp_srv, sftp_port
                )

                if files:
                    file_found_for_this_month = True
                    found_filenames = [f.get('filename') for f in files]
                    break # Stop checking steps for THIS month, move to reporting

        # Record the result for this month (Found OR Missing)
        if file_found_for_this_month:
            interval_report.append({
                'TaskID': task_id, 
                'Interval': period, 
                'Status': 'Found',
                'Files': ", ".join(found_filenames)
            })
        else:
            interval_report.append({
                'TaskID': task_id, 
                'Interval': period, 
                'Status': 'Missing', 
                'Files': 'N/A'
            })
            
    return interval_report # Return the COMPLETE list for all intervals

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
    args = argument_parser()
    current_env = args.env
    
    DICT_PATH = Path(r"P:\PriviaDataWarehouse\testing\Attribution_Data_Dictionary.xlsx")
    REPORT_PATH = r"P:\PriviaDataWarehouse\testing\Reports\Attribution_Audits"
    os.makedirs(REPORT_PATH, exist_ok=True)

    master_results = []
    db_conn = None

    try:
        # 1. Load the entire spreadsheet
        df_dict = pd.read_excel(DICT_PATH)
        db_conn = establish_snowflake_conn_key_pair()
        cursor = db_conn.cursor()

        # 2. Iterate through EVERY row in the Excel
        for _, row in df_dict.iterrows():
            taskid, table, pattern, source_file = get_task_metadata_dynamic(row, current_env)
            print(table,'fhlaHGOhgpdgpsjdgphpGHphgpoh')
            
            if not taskid or pd.isna(source_file): continue

            logger.info(f"Auditing {source_file} (Task {taskid}) in {table}")
            
            last_date = get_latest_source_date(cursor, table, source_file)
            if last_date:
                intervals = get_monthly_intervals(last_date)
                print(intervals,'giagfohgoQHOGFHAOHFOAhgoqhgoahgoaHGOHGOqh')
                steps = get_task_steps(taskid)
                creds = get_partner_info(steps[0][8]) # Uses PartnerID from the first step
                
                report_data = run_sftp_step_with_intervals(taskid, steps, pattern, intervals, creds, steps[0][7])
                
                if report_data:
                    temp_df = pd.DataFrame(report_data)
                    temp_df['Source_File_Name'] = source_file
                    temp_df['Target_Table'] = table
                    master_results.append(temp_df)

        # 3. Export the consolidated report
        if master_results:
            final_df = pd.concat(master_results, ignore_index=True)
            report_file = os.path.join(REPORT_PATH, f"Consolidated_Audit_{datetime.now().strftime('%Y%m%d')}.csv")
            final_df.to_csv(report_file, index=False)
            print(f"\n[REPORT GENERATED]: {report_file}")

    finally:
        if db_conn: db_conn.close()

if __name__ == "__main__":
    main()