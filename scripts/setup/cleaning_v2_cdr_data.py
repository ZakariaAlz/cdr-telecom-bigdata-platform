import random
import datetime
import pandas as pd
import numpy as np

# Define distribution of line types
line_type_distribution = {
    "mobile": 0.60,    # Increased due to mobile internet dominance 3G/4G
    "adsl": 0.20,      # Decreased as FTTH is replacing ADSL
    "ftth": 0.13,      # Increased due to rapid FTTH expansion
    "4g_fixed": 0.05,  # Small but significant segment
    "international": 0.02  # Small segment of international calls
}

# Define call types
call_types = {
    1: "VOICE",
    2: "SMS",
    3: "DATA"  # Used for the offers that AT gives
}

# Mobile phone prefixes by operator
MOBILE_PREFIXES = {
    # Ooreedoo prefixes
    "05": ["60", "50", "52", "51", "54", "53", "55", "56", "57", "58", "59"],
    # Mobilis prefixes
    "06": ["60", "61", "62", "63", "64", "65", "66", "67", "68", "69"],
    # Djezzy prefixes
    "07": ["70", "71", "72", "73", "74", "75", "76", "77", "78", "79"],
}

# Fixed line prefixes by type
ADSL_PREFIXES = {
    "02": ["13", "14", "15", "16", "17", "18", "19"],
    "03": ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29"],
    "04": ["30", "31", "32", "33", "34", "35", "36", "37", "38", "39"]
}

FTTH_PREFIXES = {
    "03": ["70", "71", "72", "73", "74", "75", "76", "77", "78", "79"],
    "04": ["80", "81", "82", "83", "84", "85", "86", "87", "88", "89"]
}

FIXED_4G_PREFIXES = {
    "03": ["90", "91", "92", "93", "94"],
    "04": ["95", "96", "97", "98", "99"]
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

# Map of Algerian wilayas
WILAYAS = {
    "01": "Adrar",
    "05": "Batna",
    "06": "Bejaia",
    "07": "Biskra",
    "09": "Blida",
    "10": "Bouira",
    "15": "Tizi Ouzou",
    "16": "Algiers",
    "17": "Djelfa",
    "19": "Setif",
    "23": "Annaba",
    "25": "Constantine",
    "31": "Oran",
    "35": "Boumerdas",
    "47": "Ghardaia",
}

# Inverse mapping from wilaya name to code
WILAYAS_CODE = {v: k for k, v in WILAYAS.items()}

# Map of international country codes (without +)
INTERNATIONAL_CODE_MAP = {
    "France": "33",
    "Spain": "34",
    "Germany": "49",
    "Italy": "39",
    "US/Canada": "1",
    "United Kingdom": "44",
    "Belgium": "32",
}

def generate_mobile_number():
    """Generate a random Algerian mobile number"""
    prefix = random.choice(list(MOBILE_PREFIXES.keys()))
    second_part = random.choice(MOBILE_PREFIXES[prefix])
    last_part = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"0{prefix}{second_part}{last_part}"

def generate_fixed_line_number(line_type):
    """Generate a random Algerian fixed line number based on type"""
    if line_type == "adsl":
        prefix = random.choice(list(ADSL_PREFIXES.keys()))
        second_part = random.choice(ADSL_PREFIXES[prefix])
    elif line_type == "ftth":
        prefix = random.choice(list(FTTH_PREFIXES.keys()))
        second_part = random.choice(FTTH_PREFIXES[prefix])
    elif line_type == "4g_fixed":
        prefix = random.choice(list(FIXED_4G_PREFIXES.keys()))
        second_part = random.choice(FIXED_4G_PREFIXES[prefix])
    else:
        raise ValueError(f"Unknown fixed line type: {line_type}")
    
    last_part = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    return f"0{prefix}{second_part}{last_part}"

def generate_international_number(country):
    """Generate an international number for a specific country"""
    prefix = INTERNATIONAL_PREFIX_MAP[country]
    # Generate random digits (length varies by country)
    digits = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"{prefix}{digits}"

def get_random_country():
    """Return a random country from the international prefixes"""
    return random.choice(list(INTERNATIONAL_PREFIX_MAP.keys()))

def get_random_wilaya():
    """Return a random wilaya code and name"""
    code = random.choice(list(WILAYAS.keys()))
    return code, WILAYAS[code]

def get_line_type():
    """Return a random line type based on distribution"""
    return random.choices(
        list(line_type_distribution.keys()),
        weights=list(line_type_distribution.values()),
        k=1
    )[0]

def get_call_type():
    """Return a random call type with ID"""
    call_type_id = random.choice(list(call_types.keys()))
    return call_type_id, call_types[call_type_id]

def generate_cdr_dataset(num_records=50):
    """Generate a dataset of CDR records"""
    data = []
    
    for i in range(num_records):
        # Generate a unique CDR_ID
        cdr_id = f"1.{random.randint(80, 82)}E+17"
        
        # Set common fields
        status = "A"
        start_date = "2.025E+13"  # January 1, 2025
        end_date = "2.025E+13"    # January 1, 2025
        service_category = 1
        
        # Determine call type (VOICE or DATA)
        call_type_id, _ = get_call_type()
        if call_type_id == 2:  # Convert SMS to either VOICE or DATA
            call_type_id = random.choice([1, 3])
        
        # Set usage based on call type
        if call_type_id == 1:  # VOICE
            actual_usage = random.randint(20, 180)
            rate_usage = actual_usage
            debit_amount = 0
            # Some international calls have higher debit amounts
            if random.random() < 0.2:  # 20% chance for a charged call
                debit_amount = random.randint(5, 25) * 100  # 500-2500 units
        else:  # DATA
            actual_usage = random.randint(10, 30)
            rate_usage = random.randint(20, 60)
            debit_amount = 1050  # Fixed data charge
        
        # Determine line types for caller and called
        calling_line_type = get_line_type()
        called_line_type = get_line_type()
        
        # Generate phone numbers and locations
        is_international_origin = False
        is_international_dest = False
        
        # Generate calling party number and location
        if calling_line_type == "international":
            is_international_origin = True
            calling_country = get_random_country()
            calling_number = generate_international_number(calling_country)
            calling_source = calling_country
            source_code_calling = INTERNATIONAL_CODE_MAP[calling_country]
        else:
            if calling_line_type == "mobile":
                calling_number = generate_mobile_number()
            else:
                calling_number = generate_fixed_line_number(calling_line_type)
            
            calling_wilaya_code, calling_wilaya = get_random_wilaya()
            calling_source = calling_wilaya
            source_code_calling = calling_wilaya_code
        
        # Generate called party number and location
        if called_line_type == "international":
            is_international_dest = True
            called_country = get_random_country()
            called_number = generate_international_number(called_country)
            called_destination = called_country
            source_code_called = INTERNATIONAL_CODE_MAP[called_country]
        else:
            if called_line_type == "mobile":
                called_number = generate_mobile_number()
            else:
                called_number = generate_fixed_line_number(called_line_type)
            
            called_wilaya_code, called_wilaya = get_random_wilaya()
            called_destination = called_wilaya
            source_code_called = called_wilaya_code
        
        # Set other fields
        calling_home_area = 159
        called_home_area = 118 if not is_international_dest else 500
        call_indicator = 1
        main_offering_id = random.randint(10000, 15000)
        brand_id = random.randint(100000000, 2000000000)
        pay_type = 1
        balance_type = 3000
        free_unit_amount = 0
        
        # Some calls have free units
        if random.random() < 0.15:  # 15% chance for free minutes
            free_unit_amount = actual_usage
        
        service_flow = 1
        call_forward_indicator = 0
        roam_state = 0
        online_charging_flag = 1
        
        data.append({
            "CDR_ID": cdr_id,
            "STATUS": status,
            "START_DATE": start_date,
            "END_DATE": end_date,
            "ACTUAL_USAGE": actual_usage,
            "RATE_USAGE": rate_usage,
            "DEBIT_AMOUNT": debit_amount,
            "SERVICE_CATEGORY": service_category,
            "USAGE_SERVICE_TYPE": call_type_id,
            "CallingPartyNumber": calling_number,
            "CalledPartyNumber": called_number,
            "CallingHomeAreaNumber": calling_home_area,
            "CalledHomeAreaNumber": called_home_area,
            "CallType": call_indicator,
            "MainOfferingID": main_offering_id,
            "BrandID": brand_id,
            "PayType": pay_type,
            "BALANCE_TYPE": balance_type,
            "FREE_UNIT_AMOUNT_OF_DURATION": free_unit_amount,
            "ServiceFlow": service_flow,
            "CallForwardIndicator": call_forward_indicator,
            "RoamState": roam_state,
            "OnlineChargingFlag": online_charging_flag,
            "CallingSource": calling_source,
            "CalledDestination": called_destination,
            "SourceCode_calling": source_code_calling,
            "SourceCode_Called": source_code_called
        })
    
    return pd.DataFrame(data)

# Generate a sample dataset
cdr_data = generate_cdr_dataset(50)

# Output to CSV
cdr_data.to_csv("algerian_cdr_data.csv", index=False)

print("CDR data generated successfully!")