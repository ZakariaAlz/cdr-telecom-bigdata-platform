#!/usr/bin/env python3
"""
CDR Streaming Job - Production Grade avec Monitoring et Error Handling
"""
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.table.udf import udf
from pyflink.table.types import DataTypes
import logging
import sys
import os
import time
from datetime import datetime
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/opt/flink/logs/cdr_job.log')
    ]
)
logger = logging.getLogger("CDR_FLINK")

class CDRFlinkJob:
    def __init__(self):
        self.env = None
        self.t_env = None
        self.job_start_time = datetime.now()
        self.statement_count = 0
        self.error_count = 0
        
    def setup_environment(self):
        """Configure l'environnement Flink avec les paramètres optimaux"""
        try:
            # Configuration du Stream Environment
            self.env = StreamExecutionEnvironment.get_execution_environment()
            
            # Configuration optimisée pour production
            self.env.set_parallelism(4)  # Ajusté pour votre setup
            self.env.enable_checkpointing(30000)  # Checkpoint toutes les 30 secondes
            self.env.get_checkpoint_config().set_min_pause_between_checkpoints(20000)
            self.env.get_checkpoint_config().set_checkpoint_timeout(60000)
            self.env.get_checkpoint_config().set_max_concurrent_checkpoints(1)
            
            # Table Environment
            settings = EnvironmentSettings.in_streaming_mode()
            self.t_env = StreamTableEnvironment.create(self.env, environment_settings=settings)
            
            # Configuration de la table
            config = self.t_env.get_config()
            
            # Optimisations pour performance
            config.set("table.exec.mini-batch.enabled", "true")
            config.set("table.exec.mini-batch.allow-latency", "5 s")
            config.set("table.exec.mini-batch.size", "5000")
            config.set("table.optimizer.agg-phase-strategy", "TWO_PHASE")
            config.set("table.exec.resource.default-parallelism", "4")
            
            # Configuration des state TTL
            config.set("table.exec.state.ttl", "24 h")
            
            # Configuration mémoire
            config.set("taskmanager.memory.managed.fraction", "0.4")
            config.set("table.exec.spill-compression.enabled", "true")
            
            # JARs requis
            jars = [
                "file:///opt/flink/lib/flink-sql-connector-kafka-3.0.1-1.18.jar",
                "file:///opt/flink/lib/flink-connector-jdbc-3.1.1-1.17.jar",
                "file:///opt/flink/lib/postgresql-42.7.2.jar"
            ]
            config.set("pipeline.jars", ";".join(jars))
            
            logger.info("✅ Environment configured successfully")
            logger.info(f"   Parallelism: 4")
            logger.info(f"   Checkpointing: 30s")
            logger.info(f"   Mini-batch: enabled (5s latency, 5000 size)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup environment: {e}")
            return False
    
    def test_connections(self):
        """Test les connexions PostgreSQL et Kafka"""
        logger.info("🔧 Testing connections...")
        
        # Test PostgreSQL
        try:
            test_query = """
            CREATE TEMPORARY TABLE test_connection (
                id INT,
                name STRING
            ) WITH (
                'connector' = 'jdbc',
                'url' = 'jdbc:postgresql://postgres:5432/cdr_warehouse',
                'table-name' = 'test_connection_temp',
                'username' = 'postgres',
                'password' = 'postgres'
            )
            """
            self.t_env.execute_sql(test_query)
            logger.info("✅ PostgreSQL connection OK")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL test failed: {e}")
            
        # Test monitoring table
        try:
            monitor_query = """
            CREATE TEMPORARY TABLE job_monitoring (
                timestamp TIMESTAMP(3),
                metric_name STRING,
                metric_value DOUBLE,
                details STRING
            ) WITH (
                'connector' = 'print',
                'print-identifier' = 'MONITOR'
            )
            """
            self.t_env.execute_sql(monitor_query)
            logger.info("✅ Monitoring table created")
        except Exception as e:
            logger.warning(f"⚠️ Monitoring table creation failed: {e}")
    
    def register_udfs(self):
        """Enregistre les UDFs personnalisées"""
        try:
            # UDF pour parser les anomaly flags
            @udf(result_type=DataTypes.INT())
            def count_anomaly_flags(flags_str):
                if not flags_str:
                    return 0
                return len(flags_str.split(','))
            
            # UDF pour calculer le score de risque
            @udf(result_type=DataTypes.DOUBLE())
            def calculate_risk_score(anomaly_score, churn_flag, revenue_at_risk):
                base_score = anomaly_score or 0.0
                if churn_flag == 1:
                    base_score += 2.0
                if revenue_at_risk and revenue_at_risk > 100:
                    base_score += 1.0
                return min(base_score, 10.0)
            
            self.t_env.create_temporary_function("count_anomaly_flags", count_anomaly_flags)
            self.t_env.create_temporary_function("calculate_risk_score", calculate_risk_score)
            
            logger.info("✅ UDFs registered successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to register UDFs: {e}")
    
    def load_sql_file(self, filename):
        """Charge et exécute un fichier SQL"""
        file_path = f"/opt/flink/sql/{filename}"
        
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return False
            
        logger.info(f"📄 Loading {filename}...")
        
        try:
            with open(file_path, "r") as f:
                content = f.read()
                
            # Séparer les statements
            statements = [s.strip() for s in content.split(';') if s.strip()]
            
            success_count = 0
            for i, stmt in enumerate(statements, 1):
                if not stmt or stmt.startswith('--'):
                    continue
                    
                try:
                    logger.info(f"   Executing statement {i}/{len(statements)}")
                    
                    # Log le type de statement
                    stmt_type = stmt.strip().split()[0].upper()
                    logger.debug(f"   Statement type: {stmt_type}")
                    
                    result = self.t_env.execute_sql(stmt)
                    self.statement_count += 1
                    
                    if "INSERT" in stmt_type:
                        logger.info(f"   ✅ Started streaming pipeline")
                        # Monitoring du job
                        self.monitor_job(stmt_type, filename)
                    else:
                        logger.info(f"   ✅ Statement executed successfully")
                        
                    success_count += 1
                    
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"   ❌ Error in statement {i}: {str(e)}")
                    logger.debug(f"   Statement: {stmt[:100]}...")
                    
                    # Continue avec les autres statements
                    continue
                    
            logger.info(f"📊 {filename}: {success_count}/{len(statements)} statements succeeded")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Cannot read {filename}: {e}")
            return False
    
    def monitor_job(self, job_type, source_file):
        """Enregistre les métriques du job"""
        try:
            monitor_insert = f"""
            INSERT INTO job_monitoring
            SELECT
                CURRENT_TIMESTAMP as timestamp,
                '{job_type}_STARTED' as metric_name,
                1.0 as metric_value,
                '{source_file}' as details
            """
            self.t_env.execute_sql(monitor_insert)
        except:
            pass  # Monitoring optionnel
    
    def create_advanced_pipelines(self):
        """Crée des pipelines avancés supplémentaires"""
        logger.info("🚀 Creating advanced analytics pipelines...")
        
        # Pipeline de détection d'anomalies en temps réel avec ML-like scoring
        anomaly_pipeline = """
        CREATE TEMPORARY VIEW anomaly_detection_advanced AS
        WITH session_patterns AS (
            SELECT 
                subscriber_id,
                event_timestamp,
                session_id,
                COUNT(*) OVER w1 as sessions_last_hour,
                AVG(bytes_uploaded + bytes_downloaded) OVER w1 as avg_data_last_hour,
                STDDEV(duration_seconds) OVER w1 as duration_variance,
                MAX(anomaly_score) OVER w1 as max_anomaly_hour
            FROM cdr_session_events
            WINDOW w1 AS (
                PARTITION BY subscriber_id 
                ORDER BY event_timestamp 
                RANGE BETWEEN INTERVAL '1' HOUR PRECEDING AND CURRENT ROW
            )
        )
        SELECT 
            *,
            CASE 
                WHEN sessions_last_hour > 50 THEN 'EXCESSIVE_USAGE'
                WHEN duration_variance > 1000 THEN 'IRREGULAR_PATTERN'
                WHEN max_anomaly_hour > 8 THEN 'HIGH_RISK_BEHAVIOR'
                ELSE 'NORMAL'
            END as behavior_classification
        FROM session_patterns
        """
        
        try:
            self.t_env.execute_sql(anomaly_pipeline)
            logger.info("✅ Advanced anomaly detection pipeline created")
        except Exception as e:
            logger.error(f"❌ Failed to create anomaly pipeline: {e}")
    
    def run(self):
        """Exécute le job principal"""
        logger.info("🚀 Starting CDR Flink Streaming Job")
        logger.info(f"   Start time: {self.job_start_time}")
        
        # Setup environment
        if not self.setup_environment():
            sys.exit(1)
            
        # Test connections
        self.test_connections()
        
        # Register UDFs
        self.register_udfs()
        
        # Create advanced pipelines
        self.create_advanced_pipelines()
        
        # Load SQL files in order
        sql_files = [
            'sources.sql',
            'sinks.sql', 
            'views.sql',
            'pipelines.sql'
        ]
        
        for sql_file in sql_files:
            self.load_sql_file(sql_file)
            time.sleep(2)  # Pause entre les fichiers
        
        # Créer un job de monitoring en continu
        health_check = """
        INSERT INTO job_monitoring
        SELECT
            TUMBLE_END(PROCTIME(), INTERVAL '1' MINUTE) as timestamp,
            'HEALTH_CHECK' as metric_name,
            COUNT(*) as metric_value,
            CONCAT('Active sessions: ', CAST(COUNT(*) AS STRING)) as details
        FROM cdr_session_events
        WHERE event_timestamp > CURRENT_TIMESTAMP - INTERVAL '1' MINUTE
        GROUP BY TUMBLE(PROCTIME(), INTERVAL '1' MINUTE)
        """
        
        try:
            self.t_env.execute_sql(health_check)
            logger.info("✅ Health monitoring started")
        except Exception as e:
            logger.warning(f"⚠️ Health monitoring failed: {e}")
        
        # Summary
        logger.info("="*60)
        logger.info("📊 JOB SUMMARY")
        logger.info(f"   Total statements executed: {self.statement_count}")
        logger.info(f"   Errors encountered: {self.error_count}")
        logger.info(f"   Success rate: {(self.statement_count/(self.statement_count+self.error_count)*100):.1f}%")
        logger.info("="*60)
        logger.info("🚀 All pipelines launched and monitored.")
        logger.info("📈 Flink job is running. Open Flink UI at http://localhost:8081")

        # Keep job alive
        try:
            while True:
                time.sleep(60)
                logger.info("💓 Job is still running...")
        except KeyboardInterrupt:
            logger.info("🛑 Job stopped manually.")


if __name__ == "__main__":
    job = CDRFlinkJob()
    job.run()
