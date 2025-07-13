import pandas as pd
import numpy as np
import os
import datetime
import pytz
import random
import traceback

# ----------------------Configuration--------------------

# Algerian wilaya prefixes

# ------------------ FUNCTIONS ------------------


def parse_telecom_timestamp(timestamp_str):
    """Parse telecom-specific timestamp format."""
    if pd.isna(timestamp_str) or timestamp_str == "":
        return np.nan
    try:
        # Your timestamps appear to be in format: YYYYMMDDHHMMSS
        # For example: 20241231225812
        if isinstance(timestamp_str, str) and len(timestamp_str) == 14:
            year = int(timestamp_str[0:4])
            month = int(timestamp_str[4:6])
            day = int(timestamp_str[6:8])
            hour = int(timestamp_str[8:10])
            minute = int(timestamp_str[10:12])
            second = int(timestamp_str[12:14])
            
            dt = datetime.datetime(year, month, day, hour, minute, second)
            return dt.strftime('%Y-%M-%D %H:%M:%S')
        
        # If not in expected format, try standard conversion
        if isinstance(timestamp_str, (int, float)):
            if timestamp_str > 10000000000:  # More than 10 billion means it's
                # in milliseconds
                timestamp_str = timestamp_str / 1000
            
            dt = datetime.datetime.fromtimestamp(timestamp_str, pytz.timezone(
                'Africa/Algiers'))
            return dt.strftime('%Y-%M-%D %H:%M:%S')
        
        # Return as is if we can't parse
        return str(timestamp_str)
    except Exception as e:
        print(f"Warning: Could not convert timestamp {timestamp_str}: {
            str(e)}")
        return np.nan


def get_random_prefix(line_type):
    """Get a random prefix based on line type."""
    if line_type == "mobile":
        operator = random.choices(
            population=list(operator_market_shares.keys()),
            weights=list(operator_market_shares.values()),
            k=1
        )[0]
        return random.choice(mobile_operator_prefixes[operator])
    elif line_type == "adsl":
        return random.choice(adsl_prefixes)
    elif line_type == "ftth":
        return random.choice(ftth_prefixes)
    elif line_type == "international":
        return random.choice(list(INTERNATIONAL_PREFIX_MAP.values()))
    else:
        return None


# def unix_timestamp_to_datetime(timestamp):
#     """Convert Unix timestamp to datetime string."""
#     try:
#         # If the timestamp is in milliseconds (13 digits), convert to seconds
#         if timestamp > 10000000000:  # More than 10 billion means
#             # it's in milliseconds
#             timestamp = timestamp / 1000
#         dt = datetime.datetime.fromtimestamp
#         (timestamp, pytz.timezone('Africa/Algiers'))
#         return dt.strftime('%Y-%m-%d %H:%M:%S')
#     except (ValueError, TypeError, OSError):
#         return np.nan


def standardize_phone_number(number):
    """Standardize phone numbers to a consistent format."""
    if pd.isna(number) or number == "":
        return np.nan

    number = str(number).strip()

    # Handle international Algerian numbers (+213...)
    if number.startswith('+213'):
        return '0' + number[4:]  # Remove +213 and add 0

    # Handle Algerian numbers in international format without +
    elif number.startswith('213') and len(number) > 10:
        return '0' + number[3:]  # Remove 213 and add 0

    # Handle numbers already in national format
    elif number.startswith('0'):
        return number

    # Handle other international numbers
    elif number.startswith('+'):
        # Keep as is for international numbers
        return number

    # Handle numbers without any prefix (assuming they're Algerian)
    elif len(number) >= 9:  # Most Algerian numbers are 10 digits with
        # leading 0
        return '0' + number

    # Return as is if we can't determine the format
    return number


def generate_realistic_number():
    """Generate a realistic Algerian or international phone number based on
    the2025 distribution."""
    category = random.choices(
        population=list(line_type_distribution.keys()),
        weights=list(line_type_distribution.values()),
        k=1
    )[0]

    prefix = get_random_prefix(category)

    if category == "mobile":
        # Select operator based on market share
        operator = random.choices(
            population=list(operator_market_shares.keys()),
            weights=list(operator_market_shares.values()),
            k=1
        )[0]
    # Get prefix for selected operator
        prefix = random.choice(mobile_operator_prefixes[operator])
        return f"{prefix}{random.randint(1000000, 9999999)}"

    elif category == "adsl":
        prefix = random.choice(adsl_prefixes)
        return f"{prefix}{random.randint(100000, 999999)}"

    elif category == "ftth":
        prefix = random.choice(ftth_prefixes)
        return f"{prefix}{random.randint(100000, 999999)}"

    elif category == "international":
        country, prefix = random.choice(list(INTERNATIONAL_PREFIX_MAP.items()))
        return f"{prefix}{random.randint(100000000, 999999999)}"

    else:
        return f"098{random.randint(1000000, 9999999)}"


def get_wilaya_from_number(number):
    """Determine wilaya based on phone number prefix."""
    if pd.isna(number):
        return "Unknown"

    # Standardize the number first
    std_number = standardize_phone_number(number)

    if pd.isna(std_number):
        return "Unknown"

    # International numbers don't have an Algerian wilaya
    if str(std_number).startswith('+'):
        return "International"

    for wilaya, prefixes in wilaya_prefix_map.items():
        if any(str(std_number).startswith(p) for p in prefixes):
            return wilaya

    return "Unknown"


def get_operator(number):
    """Determine mobile operator based on number prefix."""
    if pd.isna(number):
        return "Unknown"
        
    # Standardize the number first
    std_number = standardize_phone_number(number)
    
    if pd.isna(std_number):
        return "Unknown"
    
    # International numbers don't have an Algerian operator
    if str(std_number).startswith('+'):
        return "International"
    
    # Check for each operator's prefixes
    for operator, prefixes in mobile_operator_prefixes.items():
        if any(str(std_number).startswith(p) for p in prefixes):
            return operator
            
    return "Fixed Line"  # Assume it's a fixed line if
    # not matching mobile patterns


def get_line_type(number):
    """Determine line type based on phone number prefix."""
    if pd.isna(number):
        return "Unknown"
        
    # Standardize the number first
    std_number = standardize_phone_number(number)
    
    if pd.isna(std_number):
        return "Unknown"
    
    # Check for international numbers
    if str(std_number).startswith('+'):
        return "INTERNATIONAL"
        
    # Simplified line type detection based on prefix
    # In reality, this would require more sophisticated logic or
    # a database lookup
    for operator, prefixes in mobile_operator_prefixes.items():
        if any(str(std_number).startswith(p) for p in prefixes):
            return "MOBILE"
        
    if any(str(std_number).startswith(p) for p in ftth_prefixes):
        return "FTTH"
        
    if any(str(std_number).startswith(p) for p in adsl_prefixes):
        return "ADSL"
        
    return "OTHER"


# def get_call_type(type_id):
#     """Map call type ID to meaningful description."""
#     if pd.isna(type_id):
#         return "UNKNOWN"
        
#     try:
#         type_id_int = int(type_id)
#         return call_types.get(type_id_int, f"OTHER_{type_id_int}")
#     except (ValueError, TypeError):
#         return f"UNKNOWN_{type_id}"


def calculate_duration(start_date, end_date):
    """Calculate call duration in seconds from timestamps."""
    if pd.isna(start_date) or pd.isna(end_date):
        return np.nan
        
    try:
        # If timestamps are already in seconds, use as is
        #     return max(0, end_date - start_date)
        # except Exception:
        #     return np.nan
        # Parse timestamps in format YYYYMMDDHHMMSS
        start_dt = datetime.datetime.strptime(str(start_date), "%Y%m%d%H%M%S")
        end_dt = datetime.datetime.strptime(str(end_date), "%Y%m%d%H%M%S")
        
        # Calculate duration in seconds
        duration_seconds = (end_dt - start_dt).total_seconds()
        return max(0, duration_seconds)
    except Exception as e:
        print(f"Warning: Could not calculate duration: {str(e)}")
        return np.nan


def infer_wilaya(number):
    """Infer wilaya from phone number."""
    for wilaya, prefixes in wilaya_prefix_map.items():
        if any(str(number).startswith(pref) for pref in prefixes):
            return wilaya
    return "International" if str(number).startswith('+') else "Unknown"


def infer_line_type(number):
    """Infer line type from phone number."""
    number = str(number)
    if number.startswith('+'):
        return 'international'
    elif any(
        number.startswith(p)
        for p in [
            p for op_prefixes in mobile_operator_prefixes.values()
            for p in op_prefixes
        ]
    ):
        return 'mobile'
    elif number[:3] in adsl_prefixes:
        return 'adsl'
    elif number[:3] in ftth_prefixes:
        return 'ftth'
    else:
        return 'unknown'


def enrich_numbers(df):
    """Enrich phone numbers with additional information."""
    for col in ['SRC_CDR_NO', 'RECIPIENT_NUMBER']:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: x if pd.notna(x) and str(x).strip() else
                generate_realistic_number()
            )
    if 'SRC_CDR_NO' in df.columns:
        df['wilaya_source'] = df['SRC_CDR_NO'].apply(infer_wilaya)
        df['SRC_LINE_TYPE'] = df['SRC_CDR_NO'].apply(infer_line_type)
        df['SRC_OPERATOR'] = df['SRC_CDR_NO'].apply(get_operator)
    if 'RECIPIENT_NUMBER' in df.columns:
        df['wilaya_dest'] = df['RECIPIENT_NUMBER'].apply(infer_wilaya)
        df['DEST_LINE_TYPE'] = df['RECIPIENT_NUMBER'].apply(infer_line_type)
        df['DEST_OPERATOR'] = df['RECIPIENT_NUMBER'].apply(get_operator)
        # Add country information for international numbers
        df['DEST_COUNTRY'] = df['RECIPIENT_NUMBER'].apply(
            lambda x: next((country for country,
                            prefix in INTERNATIONAL_PREFIX_MAP.items()
                            if str(x).startswith(prefix)), 'Algeria'))

    return df

# ------------------ MAIN FUNCTION ------------------


def enrich_cdr_data(input_folder, output_folder, replace_numbers=True):
    """
    Process all CDR files in the input folder and
    save enriched files to output folder.

    Args:
        input_folder: Path to folder with original CDR CSVs
        output_folder: Path to save enriched CSVs
        replace_numbers: Whether to replace phone numbers with generated ones
    """
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if file.endswith(".csv"):
            print(f"Processing {file}...")

            try:
                # Read the file
                df = pd.read_csv(
                    os.path.join(input_folder, file), low_memory=False
                )

                # Keep track of original columns to ensure no data loss
                original_columns = df.columns.tolist()

                # Identify the phone number columns
                phone_columns = {
                    'CallingPartyNumber': 'calling',   # The number initiating
                    # the call
                    'CalledPartyNumber': 'called',
                    'RECIPIENT_NUMBER': 'called',
                    'SRC_CDR_NO': 'called'      
                                }     
    
                for col, party in phone_columns.items():
                    if col in df.columns:
                        print(f"Found {party} party column: {col}")
                        
                        if replace_numbers:
                            # Create a copy of original numbers before
                            #  replacing
                            df[f'ORIGINAL_{col}'] = df[col].copy()
                            df[col] = df[col].apply(
                                lambda x: generate_realistic_number())
                        else:
                            df[f'ORIGINAL_{col}'] = df[col].copy()
                            df[col] = df[col].apply(standardize_phone_number)
                        
                        # Add enrichment for this phone number
                        prefix = 'SRC_' if party == 'calling' else 'DEST_'
                        df[f'{prefix}WILAYA'] = df[col].apply(
                            get_wilaya_from_number)
                        df[f'{prefix}LINE_TYPE'] = df[col].apply(get_line_type)
                        df[f'{prefix}OPERATOR'] = df[col].apply(get_operator)
                        # Process timestamps
                time_columns = {
                    'START_DATE': 'CALL_START_TIME',
                    'END_DATE': 'CALL_END_TIME',
                    'CUST_LOCAL_START_DATE': 'LOCAL_START_TIME',
                    'CUST_LOCAL_END_DATE': 'LOCAL_END_TIME',
                    'CREATE_DATE': 'RECORD_CREATE_TIME'
                }

                # for possible_calling_col in [
                #                             'CallingPartyNumber',
                #                             'SRC_CDR_NO'
                #                             ]:
                #     if possible_calling_col in df.columns:
                #         calling_col = possible_calling_col
                #         break
                        
                # for possible_called_col in ['CalledPartyNumber',
                #                             'RECIPIENT_NUMBER']:
                #     if possible_called_col in df.columns:
                #         called_col = possible_called_col
                #         break
                
                # if replace_numbers:
                #     # Replace phone numbers with realistic ones
                #     if calling_col:
                #         df[calling_col] = df[calling_col].apply(
                #             lambda x: generate_realistic_number())
                    
                #     if called_col:
                #         df[called_col] = df[called_col].apply(
                #             lambda x: generate_realistic_number())
                # else:
                #     # Standardize existing phone numbers
                #     if calling_col:
                #         df[f'ORIGINAL_{calling_col}'] = df[calling_col].copy(
                #         )
                #         df[calling_col] = df[calling_col].apply(
                #             standardize_phone_number)
                    
                #     if called_col:
                #         df[f'ORIGINAL_{called_col}'] = df[called_col].copy()
                #         df[called_col] = df[called_col].apply(
                #             standardize_phone_number)
                
                # # Add enrichment columns
                # if calling_col:
                #     df['SRC_WILAYA'] = df[calling_col].apply(
                #         get_wilaya_from_number)
                #     df['SRC_LINE_TYPE'] = df[calling_col].apply(
                # get_line_type)
                #     df['SRC_OPERATOR'] = df[calling_col].apply(get_operator)
                
                # if called_col:
                #     df['DEST_WILAYA'] = df[called_col].apply(
                #         get_wilaya_from_number)
                #     df['DEST_LINE_TYPE'] = df[called_col].apply(
                # get_line_type)
                #     df['DEST_OPERATOR'] = df[called_col].apply(get_operator)
                # Convert timestamps if they exist

                for col, new_col in time_columns.items():
                    if col in df.columns:
                        print(f"Processing timestamp column: {col}")
                        df[new_col] = df[col].apply(parse_telecom_timestamp)
                # Calculate call duration if timestamps exist
                if 'START_DATE' in df.columns and 'END_DATE' in df.columns:
                    try:
                        df['CALL_DURATION_SEC'] = df.apply(
                            lambda row: calculate_duration(row[
                                'START_DATE'], row['END_DATE']), axis=1)
                        print("Added call duration calculation")
                    except Exception as e:
                        print(
                            f"Warning: \
                            Could not calculate call duration:  {str(e)}"
                            )
                
                # Map call type if available
                # if 'CallType' in df.columns:
                #     df['CALL_TYPE_DESC'] = df['CallType'].apply(
                # get_call_type)
                #     print("Added call type description")
                
                # # Map call type to meaningful description
                # for call_type_col in ['CallType', 'CALL_TYPE']:
                #     if call_type_col in df.columns:
                #         df['CALL_TYPE_DESC'] = df[call_type_col].apply(
                #             get_call_type)
                #         break
                
                # Add temporal features if datetime is available
                if 'CALL_START_TIME' in df.columns:
                    try:
                        df['CALL_DATETIME'] = pd.to_datetime(df[
                            'CALL_START_TIME'])
                        df['DAY_OF_WEEK'] = df['CALL_DATETIME'].dt.day_name()
                        df['HOUR_OF_DAY'] = df['CALL_DATETIME'].dt.hour
                        df['DAY_OF_MONTH'] = df['CALL_DATETIME'].dt.day
                        df['MONTH'] = df['CALL_DATETIME'].dt.month
                        df['IS_WEEKEND'] = df[
                            'CALL_DATETIME'].dt.dayofweek >= 5
                        df['IS_BUSINESS_HOURS'] = (df['HOUR_OF_DAY'] >= 9) & (
                            df['HOUR_OF_DAY'] <= 17) & (~df['IS_WEEKEND'])
                        print("Added temporal features")
                    except Exception as e:
                        print(f"Warning: Could not add temporal features: {
                            str(e)}")
                # Save the enriched file
                output_path = os.path.join(output_folder, f"enriched_{file}")
                df.to_csv(output_path, index=False)
                
                print(f"✅ Enriched {file} → {output_path}")
                print(f"   - Added {len(df.columns) - len(
                    original_columns)} new columns")
                
            except Exception as e:
                print(f"❌ Error processing {file}: {str(e)}")
                traceback.print_exc()  # Print the full error traceback
                #  for debugging
    
    print("Enrichment process completed!")


if __name__ == "__main__":
    input_folder = "../data/test_enrichment/"
    output_folder = "../data/test_output_enrichment/"

    # Set replace_numbers=True if you want to generate new
    #  realistic phone numbers
    # Set replace_numbers=False if you want to keep the
    # original numbers but standardize them
    enrich_cdr_data(input_folder, output_folder, replace_numbers=True)
