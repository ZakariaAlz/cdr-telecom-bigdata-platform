import pandas as pd
import os

# Sample the first few records from one of your files
input_folder = "../data/converted/"
sample_file = os.listdir(input_folder)[0]  # Just get the first file
# Read the first 5 rows of the CSV file
sample_df = pd.read_csv(os.path.join(input_folder, sample_file), nrows=5)

# Get column info
print("Columns in the dataset:")
for col in sample_df.columns:
    print(f"- {col}: {sample_df[col].dtype}")

# Check for missing values
print("\nMissing values per column:")
print(sample_df.isnull().sum())

# Check value distributions for key columns
print("\nSample values:")
for col in [
    'CallingPartyNumber',
    'CalledPartyNumber',
    'CDR_TYPE',
    'CALL_TYPE'
]:

    if col in sample_df.columns:
        print(f"\n{col}:")
        print(sample_df[col].head())
