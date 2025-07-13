#!/bin/bash
set -e

echo "⏳ Waiting for NameNode to become available..."
until hdfs dfs -ls / &> /dev/null; do
    echo "Still waiting for NameNode..."
    sleep 5
done
echo "✅ NameNode is now available"

echo "======================================="
echo "🚀 Starting HDFS DataNode Service..."
echo "======================================="
hdfs --daemon start datanode

echo "🔄 DataNode started. Keeping container alive..."
tail -f /dev/null
