# spark_utils.py
from pyspark.sql import SparkSession


def get_spark_session(app_name="CDR-App"):
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.master", "spark://spark-master:7077") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .config(
            "spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension"
            ) \
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog"
            ) \
        .getOrCreate()
    return spark