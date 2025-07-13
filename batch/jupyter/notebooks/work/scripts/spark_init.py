# spark_init.py
from pyspark.sql import SparkSession

def init_spark(app_name="Network Trend Analysis"):
    spark = SparkSession.builder \
        .appName(app_name) \
        .master("spark://spark-master:7077") \
        .config("spark.sql.catalogImplementation", "hive") \
        .config("spark.sql.warehouse.dir", "hdfs://namenode:9000/user/hive/warehouse") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
        .config("spark.hadoop.hive.metastore.uris", "thrift://hive-metastore:9083") \
        .config("spark.sql.execution.checkpointing.enabled", "true") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.caseSensitive", "false") \
        .config("spark.sql.session.timeZone", "UTC") \
        .config("spark.ui.showConsoleProgress", "true") \
        .enableHiveSupport() \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    spark.sparkContext.setCheckpointDir("hdfs://namenode:9000/user/spark/checkpoints")
    print(f"✅ SparkSession initialized (App: {app_name}, Spark: {spark.version})")
    print(f"✅ Hive Warehouse: {spark.conf.get('spark.sql.warehouse.dir')}")
    print(f"✅ Hive Metastore URI: {spark.conf.get('spark.hadoop.hive.metastore.uris')}")
    return spark
