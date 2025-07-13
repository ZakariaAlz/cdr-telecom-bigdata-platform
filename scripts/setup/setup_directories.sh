# Create all necessary directories
mkdir -p docker/config/{spark,hadoop,jupyter,mongodb,postgres,metabase,airflow,nifi,kafka}
mkdir -p data/{raw,processed,reference}
mkdir -p notebooks/{exploratory,modeling,reporting}
mkdir -p scripts/{setup,maintenance,import}
mkdir -p spark-apps/{batch,streaming}
mkdir -p src/{analytics,data_processing,visualization,utils}
mkdir -p tests/{unit,integration}
mkdir -p docs/{architecture,user_guides,api}
mkdir -p cdr-generator/{configs,templates,output}