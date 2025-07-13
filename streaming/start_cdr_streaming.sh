#!/bin/bash
# start_cdr_streaming.sh
# Orchestration script for CDR Streaming Pipeline with Podman Compose

cd "$(dirname "$0")"

set -e  # Arrêter si erreur

echo -e "\n🚀 CDR Streaming Pipeline Startup"
echo    "=================================\n"

# 1. Nettoyage complet de l'ancien déploiement
echo "🧹 Nettoyage de l'ancien déploiement (containers + volumes)..."
podman-compose -f docker-compose-streaming.yml down -v

# 2. Démarrage de Zookeeper & Postgres (bases nécessaires)
echo -e "\n🏗️ Démarrage de l'infrastructure de base (Zookeeper, Postgres)..."
podman-compose -f docker-compose-streaming.yml up -d zookeeper postgres
sleep 12

# 3. Démarrage des brokers Kafka (après ZK up)
echo -e "\n📨 Démarrage du cluster Kafka..."
podman-compose -f docker-compose-streaming.yml up -d broker1 broker2 broker3
sleep 18

# 4. Démarrage du cluster Flink
echo -e "\n⚡ Démarrage du cluster Flink (JobManager + TaskManager)..."
podman-compose -f docker-compose-streaming.yml up -d flink-jobmanager flink-taskmanager
sleep 18

# 5. Démarrage du monitoring & UI
echo -e "\n📊 Démarrage du monitoring (Prometheus, Grafana, Kafka-UI)..."
podman-compose -f docker-compose-streaming.yml up -d prometheus grafana kafka-ui
sleep 8

# 6. Démarrage des exporters (JMX, Kafka, Postgres)
echo -e "\n🧩 Démarrage des exporters de métriques..."
podman-compose -f docker-compose-streaming.yml up -d jmx-exporter-broker1 jmx-exporter-broker2 jmx-exporter-broker3 kafka-exporter postgres-exporter
sleep 8

# 7. Démarrage du générateur CDR
echo -e "\n🎯 Démarrage du générateur de CDR..."
podman-compose -f docker-compose-streaming.yml up -d cdr-generator
sleep 5

# 8. Lancement éventuel du client Flink SQL et soumission du job Python
echo -e "\n🔄 Lancement du client Flink SQL (optionnel)..."
podman-compose -f docker-compose-streaming.yml up -d flink-sql-client
sleep 5

# Soumission du job Python Flink si besoin (décommente si tu utilises du PyFlink)
# echo -e "\n🔄 Soumission du job Flink Python..."
# podman exec flink-jobmanager python /opt/flink/sql/cdr_flink_job.py

echo -e "\n✅ Pipeline démarré avec succès !"
echo    "================================="
echo    "🔗 Accès aux interfaces :"
echo    "  - Kafka UI     : http://localhost:8085"
echo    "  - Flink UI     : http://localhost:8081"
echo    "  - Grafana      : http://localhost:3000 (admin/admin)"
echo    "  - Prometheus   : http://localhost:9090"
echo    ""
echo    "📊 Pour surveiller la génération :"
echo    "    podman logs -f cdr-generator"
echo    "    podman exec broker1 kafka-console-consumer --bootstrap-server broker1:9092 --topic cdr-session-events --max-messages 5"
echo    ""
echo    "🛑 Pour stopper tout proprement :"
echo    "    podman-compose -f docker-compose-streaming.yml down -v"
echo    ""
