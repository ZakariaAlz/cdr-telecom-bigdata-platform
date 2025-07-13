import pandas as pd

# Path to your enriched file (update if needed)
file_path = "../data/test_output_enrichment" \
            "/enriched_cbs_cdr_voice_20250101_171_101_076193_AT.add_Sheet1.csv"

# Load the file
df = pd.read_csv(file_path)

# Show the first 5 rows
print(df.head())

# Show the shape (rows, columns)
print("Shape:", df.shape)

# Optional: show a subset of relevant columns
cols_to_view = [
    'CallingPartyNumber', 'CalledPartyNumber', 'SRC_CDR_NO',
    'RECIPIENT_NUMBER', 'wilaya_source', 'wilaya_dest'
    ]
print(df[cols_to_view].sample(10))  # Random 10 rows
