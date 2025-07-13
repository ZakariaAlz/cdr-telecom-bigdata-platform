# kafka/producer/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    kafka-python==2.0.2 \
    numpy==1.24.3 \
    prometheus-client==0.19.0

# Copy application files
COPY . .

# Expose metrics port
EXPOSE 8000

# Default command
CMD ["python", "cdr_stream_gen.py", "--config", "streaming_config.json", "--rate", "400"]