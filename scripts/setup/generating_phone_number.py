import pandas as pd
import random

# Constants for Wilaya Fixed-line Prefix Mapping (for ADSL, FTTH)
WILAYA_PREFIX_MAP = {
    'Algiers': ['021', '023', '044'],  # First prefix is for ADSL
    'Oran': ['041', '042'],
    'Constantine': ['031', '043'],
    'Annaba': ['038', '045'],
    'Bejaia': ['034', '046'],
    'Tizi Ouzou': ['026', '047'],
    'Blida': ['025', '048'],
    'Setif': ['036', '049'],
    'Batna': ['033', '039'],
    'Tlemcen': ['043', '032'],
    'Mostaganem': ['045', '037'],
    'Boumerdas': ['024', '050'],
}

# Constants for Mobile Operators (4G/LTE prefixes)
MOBILE_OPERATOR_PREFIX_MAP = {
    "Ooredoo": ["0550", "0560"],
    "Mobilis": ["0660", "0661"],
    "Djezzy": ["0770", "0772"],
}

# Constants for ADSL and FTTH fixed-line numbers, they're mentioned in the
# original wilaya_prefix_map
ADSL_FTTH_PREFIX_MAP = {
    "ADSL": [
        "021", "023", "041", "031", "038", "034", "026", "025", "048",
        "036",  "033", "043", "045"],  # ADSL prefixes for Algeria

    "FTTH": [
        "044", "042", "043", "045", "046", "047",
        "049", "032", "037", "039"],  # FTTH prefixes for Algeria
}

# 2025 Internet distribution (based on provided statistics and projections)
# These represent the probabilities of a random number being of each type
line_type_distribution = {
    "mobile": 0.60,     # Increased due to mobile internet dominance 3G/4G
    "adsl": 0.20,       # Decreased as FTTH is replacing ADSL
    "ftth": 0.13,       # Increased due to rapid FTTH expansion
    "4g_fixed": 0.05,   # Small but significant segment
    "international": 0.02  # Small segment of international calls
}
# Constants for VOIP and Emergency Numbers
EMERGENCY_NUMBERS = {
    "Police": "1548",
    "Fire": "14",
    "Gendarme": "1055",
    "Coast Guard": "1054",
}

# International country phone number prefixes (for Algerians living abroad)
INTERNATIONAL_PREFIX_MAP = {
    "France": "+33",
    "Spain": "+34",
    "Germany": "+49",
    "Italy": "+39",
    "US/Canada": "+1",
    "United Kingdom": "+44",
    "Belgium": "+32",
}


def generate_call_pattern(num_records, population_distribution=None):
    """
    Generate a realistic call pattern based on population distribution

    Args:
        num_records: Number of call records to generate
        population_distribution: Dictionary of regions
        and their population percentages

    Returns:
        DataFrame with call pattern information
    """
    if population_distribution is None:
        # Default population distribution by wilaya (approximate percentages)
        population_distribution = {
            "Algiers": 0.15,      # Capital region
            "Oran": 0.08,
            "Boumerdas": 0.09,       # Second largest city
            "Constantine": 0.06,  # Third largest city
            "Annaba": 0.04,
            "Bejaia": 0.04,
            "Tizi Ouzou": 0.04,
            "Blida": 0.05,
            "Setif": 0.06,
            "Batna": 0.04,
            "Tlemcen": 0.04,
            "Adrar": 
            "Gherdaia":
            "Bechar": 
            "Other": 0.31      # Remaining wilayas combined
        }


# Call Types (Focus on voice data as specified)
call_types = {
    1: "VOICE",
    2: "SMS",
    3: "DATA",
    4: "MMS",
    5: "VOICE_ROAMING",
    6: "SMS_ROAMING",
    7: "DATA_ROAMING",
    8: "MMS_ROAMING"
}


# Function to generate phone numbers based on regions (wilayas in Algeria)
def generate_fixed_number(region, line_type='ADSL'):
    """
    Generate a fixed number based on the region (wilaya) and line type.

    Args:
        region (str): The wilaya (region) name.
        line_type (str): The type of line ('ADSL' or 'FTTH').

    Returns:
        str: A generated fixed-line phone number.
    """
    # Determine the prefix map based on the line type
    prefix_map = (
        ADSL_FTTH_PREFIX_MAP if line_type in ['ADSL', 'FTTH'] 
        else WILAYA_PREFIX_MAP
    )
    # Select a prefix and generate the number
    prefix = random.choice(prefix_map.get(region, ["021"]))
    number = f"{prefix}{random.randint(1000000, 9999999)}"
    return number


# Function to generate phone numbers based on mobile network types
def generate_mobile_number(operator):
    """Generate a mobile number based on the operator."""
    prefix = random.choice(MOBILE_OPERATOR_PREFIX_MAP.get(operator, ["052"]))
    number = f"{prefix}{random.randint(1000000, 9999999)}"
    return number


# Function to extract wilaya based on phone number prefix
def get_wilaya_from_number(number):
    """Extract the wilaya (region) from a phone number."""
    for wilaya, prefixes in WILAYA_PREFIX_MAP.items():
        if any(number.startswith(prefix) for prefix in prefixes):
            return wilaya
    return "Unknown"  # If no match is found


# Function to determine line type (ADSL, Fiber-to-the-Home (FTTH), 4G/LTE)
def get_line_type_from_number(number):
    """Determine the line type (ADSL, Fiber-to-the-Home (FTTH), or 4G/LTE) 
    based on the number prefix."""
    for prefixes in ADSL_FTTH_PREFIX_MAP.values():
        if any(number.startswith(prefix) for prefix in prefixes):
            return "ADSL/FTTH"
    for prefixes in MOBILE_OPERATOR_PREFIX_MAP.values():
        if any(number.startswith(prefix) for prefix in prefixes):
            return "4G/LTE"
    return "Unknown"


# Load your CSV data into pandas DataFrame
df = pd.read_csv("converted/")  # Adjust the path accordingly

# Enriching calling and recipient numbers with wilaya (region) info
# "Wilaya" refers to administrative regions in Algeria.
df['SRC_REGION'] = df['SRC_CDR_NO'].apply(
    lambda x: get_wilaya_from_number(str(x))
)
df['DEST_REGION'] = df['RECIPIENT_NUMBER'].apply(
    lambda x: get_wilaya_from_number(str(x))
)

# Enriching line types based on phone numbers
df['SRC_LINE_TYPE'] = df['SRC_CDR_NO'].apply(
    lambda x: get_line_type_from_number(str(x))
)
df['DEST_LINE_TYPE'] = df['RECIPIENT_NUMBER'].apply(
    lambda x: get_line_type_from_number(str(x))
)

# If numbers are missing or anonymized, generate new ones
# "FTTH" refers to Fiber-to-the-Home technology.
df['SRC_CDR_NO'] = df.apply(
    lambda row: generate_fixed_number("Algiers", line_type='FTTH')
    if pd.isna(row['SRC_CDR_NO']) else row['SRC_CDR_NO'],
    axis=1
)

df['RECIPIENT_NUMBER'] = df.apply(
    lambda row: generate_fixed_number("Oran", line_type='ADSL')
    if pd.isna(row['RECIPIENT_NUMBER']) else row['RECIPIENT_NUMBER'],
    axis=1
)

# Final selection of columns to keep for the Data Engineering Project
columns_to_keep = [
    "CDR_ID", "CDR_TYPE", "START_DATE", "END_DATE", "CallingPartyNumber",
    "CalledPartyNumber", "TERMINATION_REASON", "ACTUAL_USAGE", "STATUS",
    "CallingRoamInfo", "CallingCellID", "DEBIT_AMOUNT", "TOTAL_TAX",
    "ROAM_STATE", "CALL_TYPE",  # Call type (voice, data, etc.)
    "DEST_LINE_TYPE",  # Destination line type (ADSL, FTTH, 4G/LTE)
    "SRC_CDR_NO",  # Source phone number
    "SRC_REGION",  # Region (wilaya) for the source number
    "SRC_LINE_TYPE",  # Type of source line (FTTH, ADSL, 4G/LTE)
    "DEST_REGION",  # Region (wilaya) for the recipient's number
    "DEST_COUNTRY",  # Country for international calls
]

# Keep only the selected columns
df = df[columns_to_keep]

# Optionally, save the enriched dataset
df.to_csv("enriched_cdr_with_wilayas.csv", index=False)

print("Enrichment and processing completed successfully!")
