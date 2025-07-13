#!/bin/bash
set -e

echo "🔁 Restarting batch stack..."
podman-compose -f docker-compose-batch.yml down || true
podman-compose -f docker-compose-batch.yml build
podman-compose -f docker-compose-batch.yml up -d

sleep 5

echo ""
echo "🔍 Verifying containers..."
for service in namenode datanode1 datanode2 hive-metastore-db hive-metastore hiveserver2 spark-master spark-worker-1 spark-worker-2 jupyter superset-db superset airflow; do
    if podman inspect -f '{{.State.Status}}' "$service" 2>/dev/null | grep -q running; then
        echo "✅ $service is running"
    else
        echo "❌ $service is NOT running. Run: podman logs $service"
    fi
done

echo ""
echo "📍 UI Access:"
echo "  - 🧪 JupyterLab:        http://localhost:8888"
echo "  - 📊 Superset:          http://localhost:8088"
echo "  - ☁️ Airflow:           http://localhost:8070"
echo "  - 🧠 Spark Master UI:   http://localhost:8080"
echo "  - 📂 HDFS NameNode UI:  http://localhost:9870"
