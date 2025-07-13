import pandas as pd
from pathlib import Path

RAW_FOLDER = Path("../data/raw/processed_cdrs/")
CONVERTED_FOLDER = Path("../data/converted")

# Print absolute path being used
print(f"📁 Looking in: {RAW_FOLDER.resolve()}")

# Create the converted folder if it doesn't exist
CONVERTED_FOLDER.mkdir(parents=True, exist_ok=True)

# Get list of Excel files
xlsx_files = list(RAW_FOLDER.glob("*.xlsx"))

# Check if any Excel files were found
if not xlsx_files:
    print("⚠️ No Excel files found in ../data/raw/processed_cdrs/")
    print("   Please check the directory or add Excel files to convert.")
else:
    print(f"🔍 Found {len(xlsx_files)} Excel file(s):")
    for f in xlsx_files:
        print("   →", f.name)

    # Convert each Excel file
    for file_path in xlsx_files:
        try:
            print(f"\n📄 Processing: {file_path.name}")
            excel_file = pd.ExcelFile(file_path)
            print("   Sheets:", excel_file.sheet_names)

            for sheet_name in excel_file.sheet_names:
                df = excel_file.parse(sheet_name)
                output_filename = f"{file_path.stem}_{sheet_name}.csv"
                output_path = CONVERTED_FOLDER / output_filename
                df.to_csv(output_path, index=False)
                print(f"   ✅ Converted: {sheet_name} → {output_filename}")

        except Exception as e:
            print(f"   ❌ Error processing {file_path.name}: {e}")

            # Skip temporary Excel lock files
# if file_path.name.startswith("~$"):
#     print(f"⚠️ Skipping temporary file: {file_path.name}")
