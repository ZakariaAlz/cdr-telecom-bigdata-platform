import pandas as pd
from pathlib import Path

RAW_FOLDER = Path("../data/test_output_enrichment/")
CONVERTED_FOLDER = Path("../data/excel_test/")

# Print absolute path being used
print(f"📁 Looking in: {RAW_FOLDER.resolve()}")

# Create the converted folder if it doesn't exist
CONVERTED_FOLDER.mkdir(parents=True, exist_ok=True)

# Get list of Csv files
csv_files = list(RAW_FOLDER.glob("*.csv"))

# Check if any Excel files were found
if not csv_files:
    print("⚠️ No CSV files found in ../data/test_output_enrichment/")
    print("   Please check the directory or add CSV files to convert.")
else:
    print(f"🔍 Found {len(csv_files)} CSV file(s):")
    for f in csv_files:
        print("   →", f.name)

    # Convert each CSV file to Excel
    for file_path in csv_files:
        try:
            print(f"\n📄 Processing: {file_path.name}")
            df = pd.read_csv(file_path)

            output_filename = f"{file_path.stem}.xlsx"
            output_path = CONVERTED_FOLDER / output_filename
         
            df.to_excel(output_path, index=False)
            print(f"   ✅ Converted to Excel: {output_filename}")

        except Exception as e:
            print(f"   ❌ Error processing {file_path.name}: {e}")