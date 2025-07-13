FROM jupyter/base-notebook:python-3.11

# Environment setup
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 \
    SPARK_VERSION=3.5.1 \
    HADOOP_VERSION=3.4.1 \
    HIVE_VERSION=4.0.0 \
    SPARK_HOME=/opt/spark \
    HADOOP_HOME=/opt/hadoop \
    PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin:$HADOOP_HOME/bin \
    PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.5-src.zip:$PYTHONPATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

USER root

# Install dependencies
RUN apt-get update && \
    apt-get install -y openjdk-11-jdk curl wget netcat unzip procps && \
    rm -rf /var/lib/apt/lists/*

# Install Hadoop
RUN wget https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz && \
    tar -xzf hadoop-${HADOOP_VERSION}.tar.gz -C /opt && \
    mv /opt/hadoop-${HADOOP_VERSION} /opt/hadoop && \
    rm hadoop-${HADOOP_VERSION}.tar.gz

# Install Spark
RUN wget https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop3.tgz -C /opt && \
    mv /opt/spark-${SPARK_VERSION}-bin-hadoop3 /opt/spark && \
    rm spark-${SPARK_VERSION}-bin-hadoop3.tgz

# Add Hive and Delta Lake support
RUN mkdir -p $SPARK_HOME/jars && \
    curl -o $SPARK_HOME/jars/postgresql-42.5.1.jar https://repo1.maven.org/maven2/org/postgresql/postgresql/42.5.1/postgresql-42.5.1.jar && \
    curl -o $SPARK_HOME/jars/delta-core_2.12-2.4.0.jar https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.4.0/delta-core_2.12-2.4.0.jar && \
    curl -o $SPARK_HOME/jars/delta-storage-2.4.0.jar https://repo1.maven.org/maven2/io/delta/delta-storage/2.4.0/delta-storage-2.4.0.jar

# (Optional) Download Hive-Spark integration JARs if you have a trusted source
# You may add these manually in the volume mapped to /home/jovyan/work or /opt/spark/jars   

# Create config directories
RUN mkdir -p /opt/spark/conf /etc/hadoop/conf

USER $NB_UID

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
        pyspark==${SPARK_VERSION} \
        findspark \
        numpy pandas matplotlib seaborn plotly pyarrow \
        delta-spark hdfs sqlalchemy ipywidgets ipython notebook jupyterlab \
        scikit-learn xgboost lightgbm tensorflow keras torch \
        python-dotenv psycopg2-binary mysql-connector-python \
        pyhive "pyhive[mysql]" "pyhive[postgresql]" "pyhive[presto]" \
        great_expectations

WORKDIR /home/jovyan/work
EXPOSE 8888
CMD ["start-notebook.sh","--NotebookApp.token='zaki123'","--NotebookApp.password=''"]
