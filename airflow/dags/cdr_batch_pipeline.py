from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import (
    SparkSubmitOperator
)
from datetime import datetime
x
default_args = {
    'start_date': datetime(2024, 1, 1),
    'retries': 1
}

with DAG(
    'cdr_batch_ingestion',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False
) as dag:

    spark_job = SparkSubmitOperator(
        task_id='run_cdr_batch_job',
        application='/opt/spark-apps/cdr_batch_job.py',  # Your Spark Job path
        conn_id='spark_default',
        executor_memory='4g',
        driver_memory='2g'
    )
