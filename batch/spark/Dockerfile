FROM bitnami/spark:3.5.1

USER root

# --- Install Python 3.10 & system dependencies ---
RUN apt-get update && \
    apt-get install -y software-properties-common curl && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y python3.10 python3.10-distutils python3.10-venv build-essential && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 && \
    ln -sf /usr/bin/python3.10 /usr/bin/python && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Upgrade pip & install Python libraries for Data Engineering/Science/Notebook ---
RUN python3.10 -m pip install --upgrade pip && \
    python3.10 -m pip install \
        jupyterlab ipykernel notebook \
        numpy pandas matplotlib seaborn plotly \
        scikit-learn \
        pyarrow fastparquet deltalake \
        openpyxl xlrd \
        requests tqdm \
        pyspark \
        sqlalchemy \
        ipywidgets \
        beautifulsoup4 \
        tabulate \
        lxml && \
    python3.10 -m ipykernel install --user --name=python310 --display-name "Python 3.10 (Spark)"

# --- Set Spark to use Python 3.10 everywhere ---
ENV PYSPARK_PYTHON=python3.10
ENV PYSPARK_DRIVER_PYTHON=python3.10

# --- Expose Jupyter port if needed ---
EXPOSE 8888

USER 1001
