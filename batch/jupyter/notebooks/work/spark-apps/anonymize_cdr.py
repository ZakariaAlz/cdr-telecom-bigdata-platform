import sys
import os
import hashlib
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

# Import Spark init from your central script
sys.path.append('/home/jovyan/work/scripts')
from spark_init import init_spark  # or from spark-init import init_spark if you use underscore or dash

def hash_value(value, salt="random_salt_2025"):
    if value is None:
        return None
    return hashlib.sha256(f"{salt}{value}".encode()).hexdigest()

def get_hash_udf(salt):
    return F.udf(lambda x: hash_value(x, salt), StringType())

def anonymize_cdr(input_path, output_path, salt, pii_columns):
    spark = init_spark("CDR Anonymization")
    df = spark.read.option("header", True).csv(input_path)
    print(f"Read {df.count()} rows from {input_path}")

    hash_udf = get_hash_udf(salt)
    for col in pii_columns:
        if col in df.columns:
            df = df.withColumn(col, hash_udf(F.col(col)))
            print(f"Anonymized column: {col}")
        else:
            print(f"Column {col} not found, skipping.")

    df.write.mode("overwrite").parquet(output_path)
    print(f"Anonymized data saved to {output_path}")

    spark.stop()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python anonymize_cdr.py <input_csv> <output_parquet> <salt>")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_parquet = sys.argv[2]
    salt = sys.argv[3]
    pii_columns = [
        "MSISDN", "IMSI", "IMEI", "CALLING_NBR", "CALLED_NBR",
        "FIXED_NUMBER", "MOBILE_NUMBER", "SUBSCRIBER_ID"
    ]
    anonymize_cdr(input_csv, output_parquet, salt, pii_columns)
