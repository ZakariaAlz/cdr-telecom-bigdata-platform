#!/usr/bin/env python3
"""
CDR Streaming Generator - Algérie Télécom (Version Ultimate Production-Ready)
Auteur: Zakaria + Claude
Version: 2.0.0
"""

import json
import time
import random
import uuid
import logging
import sys
import threading
import signal
import socket
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import numpy as np

from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Configuration des métriques Prometheus
event_counter = Counter('cdr_events_generated_total', 'Total CDR events generated', ['event_type'])
anomaly_counter = Counter('cdr_anomaly_events_total', 'Total anomaly events flagged')
active_sessions_gauge = Gauge('cdr_active_sessions', 'Active CDR sessions in memory')
processing_time_histogram = Histogram('cdr_processing_seconds', 'Time spent processing CDR events')
kafka_send_histogram = Histogram('cdr_kafka_send_seconds', 'Time spent sending to Kafka')
error_counter = Counter('cdr_generator_errors_total', 'Total errors in generator', ['error_type'])

# Démarrer le serveur de métriques Prometheus sur le bon port
start_http_server(8000)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('cdr_generator.log')
    ]
)
logger = logging.getLogger("CDR_STREAM_GEN")

@dataclass
class StreamingCDREvent:
    """Structure complète d'un événement CDR pour le streaming"""
    event_timestamp: str
    ingestion_timestamp: str
    event_id: str
    event_type: str
    subscriber_id: str
    msisdn: str
    imsi: str
    imei: str
    session_id: str
    service_type: str
    session_state: str
    cell_id: str
    lac: str
    mcc: str
    mnc: str
    wilaya: str
    network_type: str
    serving_node: str
    duration_seconds: int
    bytes_uploaded: int
    bytes_downloaded: int
    packets_lost: int
    latency_ms: float
    jitter_ms: float
    qos_class: str
    signal_strength_dbm: int
    snr_db: float
    ber: float
    charging_state: str
    current_charge: float
    rate_plan_id: str
    roaming_partner: Optional[str]
    anomaly_flags: List[str]
    anomaly_score: float
    congestion_level: str
    customer_segment: str = ""
    customer_lifetime_value: float = 0.0
    churn_risk_flag: int = 0
    revenue_this_month: float = 0.0
    num_distinct_cells_visited: int = 0
    top_app_category: str = ""
    revenue_at_risk: float = 0.0
    qos_alert_level: str = "OK"
    is_roaming: int = 0
    sessions_last_24h: int = 0
    data_usage_rolling_mb: float = 0.0
    processing_node: str = ""
    schema_version: str = "3.0"


class StreamingCDRGenerator:
    """Générateur de CDR en streaming pour Algérie Télécom"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.running = True
        self.hostname = socket.gethostname()
        
        # Configuration Kafka avec toutes les optimisations
        brokers = config.get('kafka_brokers', ['broker1:9092', 'broker2:9093', 'broker3:9094'])
        self.kafka_config = {
            'bootstrap_servers': ','.join(brokers),
            'value_serializer': lambda v: json.dumps(v, default=str).encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            'acks': 'all',
            'retries': 3,
            'compression_type': 'snappy',
            'batch_size': 16384,
            'linger_ms': 10,
            'buffer_memory': 33554432,
            'max_in_flight_requests_per_connection': 1,
            'enable_idempotence': True,  # Éviter les doublons
            'client_id': f'cdr-generator-{self.hostname}'
        }
        
        # Initialisation des composants
        self._init_kafka()
        self.active_sessions = {}
        self.subscriber_pool = self._init_subscriber_pool()
        self.cell_towers = self._init_cell_towers()
        self.network_nodes = self._init_network_nodes()
        self.metrics = defaultdict(int)
        self.customer_stats = defaultdict(lambda: {
            "lifetime_value": 0.0,
            "revenue_this_month": 0.0,
            "sessions_last_24h": deque(maxlen=1000),
            "distinct_cells": set(),
            "data_usage_rolling_mb": deque(maxlen=1000),
            "top_app_cat": "",
            "churn_flag": 0,
            "last_activity": datetime.now()
        })
        
        logger.info(f"✅ CDR Generator initialized on {self.hostname}")
        logger.info(f"📡 Kafka brokers: {brokers}")

    def _init_kafka(self):
        """Initialise la connexion Kafka et crée les topics nécessaires"""
        try:
            self.producer = KafkaProducer(**self.kafka_config)
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                client_id=f'cdr-generator-admin-{self.hostname}'
            )
            self._ensure_topics_exist()
            logger.info("✅ Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kafka: {e}")
            error_counter.labels(error_type='kafka_init').inc()
            raise

    def _ensure_topics_exist(self):
        """Crée les topics Kafka s'ils n'existent pas déjà"""
        topics_config = [
            {
                'name': 'cdr-session-events',
                'partitions': 8,
                'replication_factor': min(3, len(self.kafka_config['bootstrap_servers'])),
                'config': {
                    'retention.ms': '172800000',  # 2 jours
                    'compression.type': 'snappy',
                    'segment.ms': '3600000',  # 1 heure
                    'min.insync.replicas': '2'
                }
            },
            {
                'name': 'cdr-anomalies',
                'partitions': 4,
                'replication_factor': min(3, len(self.kafka_config['bootstrap_servers'])),
                'config': {
                    'retention.ms': '604800000',  # 7 jours
                    'compression.type': 'snappy'
                }
            },
            {
                'name': 'cdr-qos-metrics',
                'partitions': 4,
                'replication_factor': min(2, len(self.kafka_config['bootstrap_servers'])),
                'config': {
                    'retention.ms': '86400000',  # 1 jour
                    'compression.type': 'snappy'
                }
            },
            {
                'name': 'cdr-business-kpi',
                'partitions': 4,
                'replication_factor': min(2, len(self.kafka_config['bootstrap_servers'])),
                'config': {
                    'retention.ms': '259200000',  # 3 jours
                    'cleanup.policy': 'compact,delete'
                }
            },
            {
                'name': 'cdr-session-enriched',
                'partitions': 2,
                'replication_factor': min(2, len(self.kafka_config['bootstrap_servers'])),
                'config': {
                    'retention.ms': '172800000',  # 2 jours
                    'cleanup.policy': 'compact'
                }
            }
        ]
        
        for topic_config in topics_config:
            topic = NewTopic(
                name=topic_config['name'],
                num_partitions=topic_config['partitions'],
                replication_factor=topic_config['replication_factor'],
                topic_configs=topic_config['config']
            )
            try:
                self.admin_client.create_topics([topic])
                logger.info(f"✅ Created topic: {topic_config['name']}")
            except TopicAlreadyExistsError:
                logger.info(f"ℹ️ Topic already exists: {topic_config['name']}")
            except Exception as e:
                logger.error(f"❌ Failed to create topic {topic_config['name']}: {e}")
                error_counter.labels(error_type='topic_creation').inc()

    def _init_subscriber_pool(self) -> List[Dict]:
        """Initialise le pool d'abonnés avec des profils réalistes"""
        pool_size = self.config.get('subscriber_pool_size', 30000)
        segments = list(self.config["subscriber_segments"].keys())
        segment_probs = list(self.config["subscriber_segments"].values())
        wilayas = self.config["algerian_wilayas"]
        operators = self.config["operators"]
        app_cats = self.config["app_categories"]
        activity_patterns = list(self.config["activity_patterns"].keys())
        activity_probs = list(self.config["activity_patterns"].values())
        rate_plans = self.config["rate_plans"]
        
        pool = []
        for i in range(pool_size):
            op = np.random.choice(operators, p=[op['market_share'] for op in operators])
            segment = np.random.choice(segments, p=segment_probs)
            city = random.choice(wilayas)
            
            # Profil utilisateur enrichi
            subscriber = {
                'subscriber_id': f'DZ{i:07d}',
                'msisdn': f'+213{random.choice(op["prefixes"])[1:]}{random.randint(1000000, 9999999)}',
                'imsi': f'603{op["mnc"]}{random.randint(1000000000, 9999999999)}',
                'imei': f'{random.randint(100000000000000, 999999999999999)}',
                'operator': op['name'],
                'city': city,
                'segment': segment,
                'rate_plan': random.choice(rate_plans),
                'activity_pattern': np.random.choice(activity_patterns, p=activity_probs),
                'top_app_category': np.random.choice(app_cats),
                'device_type': np.random.choice(['smartphone', 'feature_phone', 'tablet', 'modem'],
                                               p=[0.7, 0.15, 0.1, 0.05])
            }
            pool.append(subscriber)
        
        logger.info(f"📱 Generated {pool_size} subscriber profiles")
        return pool

    def _init_cell_towers(self) -> List[Dict]:
        """Initialise les tours cellulaires par wilaya"""
        wilayas = self.config["algerian_wilayas"]
        network_types = list(self.config["network_technologies"].keys())
        network_probs = list(self.config["network_technologies"].values())
        
        towers = []
        tid = 0
        
        for wilaya in wilayas:
            # Plus de tours dans les grandes villes
            if wilaya == "Alger":
                num_towers = random.randint(150, 200)
            elif wilaya in ["Oran", "Constantine", "Annaba"]:
                num_towers = random.randint(80, 120)
            else:
                num_towers = random.randint(20, 60)
            
            for _ in range(num_towers):
                net_type = np.random.choice(network_types, p=network_probs)
                towers.append({
                    "cell_id": f"{wilaya[:3].upper()}{tid:05d}",
                    "lac": f"LAC{tid//20:04d}",
                    "wilaya": wilaya,
                    "mcc": "603",
                    "mnc": random.choice(["01", "02", "03"]),
                    "technology": net_type,
                    "capacity": random.randint(100, 1000),
                    "current_load": 0
                })
                tid += 1
        
        logger.info(f"📡 Generated {len(towers)} cell towers")
        return towers

    def _init_network_nodes(self) -> Dict:
        """Initialise les nœuds réseau (MSC, SGSN, etc.)"""
        return {
            'MSC': [f'MSC-{i}' for i in range(1, 6)],
            'SGSN': [f'SGSN-{i}' for i in range(1, 4)],
            'GGSN': [f'GGSN-{i}' for i in range(1, 3)],
            'MME': [f'MME-{i}' for i in range(1, 4)],
            'SGW': [f'SGW-{i}' for i in range(1, 3)],
            'PGW': [f'PGW-{i}' for i in range(1, 3)]
        }

    def _get_activity_multiplier(self, hour: int, pattern: str, day_of_week: int) -> float:
        """Calcule le multiplicateur d'activité selon l'heure et le pattern"""
        # Ajustement week-end
        is_weekend = day_of_week >= 5
        
        if pattern == "morning_heavy":
            base = 2.0 if 7 <= hour <= 10 else 0.8
        elif pattern == "evening_heavy":
            base = 2.0 if 17 <= hour <= 21 else 0.8
        elif pattern == "night_owl":
            base = 1.8 if hour in [22, 23, 0, 1, 2] else 0.6
        elif pattern == "business_hours":
            base = 1.8 if 8 <= hour <= 17 and not is_weekend else 0.7
        elif pattern == "weekend_warrior":
            base = 2.0 if is_weekend else 0.9
        else:  # balanced
            base = 1.0
        
        # Pic d'activité pendant le Ramadan (19h-21h)
        if self.config.get('ramadan_mode', False) and 19 <= hour <= 21:
            base *= 1.5
        
        return base

    def _detect_anomalies(self, event: Dict) -> Tuple[List[str], float, str, float, str]:
        """Détection avancée d'anomalies avec scoring"""
        flags = []
        score = 0.0
        
        # Vérifications basiques
        if event['service_type'] == 'VOICE' and event['duration'] > 7200:
            flags.append('LONG_DURATION_CALL')
            score += 3.0
        
        if event['service_type'] == 'DATA' and event['data_volume'] > 1024*1024*1024:  # 1GB
            flags.append('EXCESSIVE_DATA_USAGE')
            score += 2.5
        
        if event['latency'] > 200:
            flags.append('HIGH_LATENCY')
            score += 1.5
        
        if event['signal'] < -100:
            flags.append('LOW_SIGNAL')
            score += 1.0
        
        if event['roaming']:
            flags.append('IS_ROAMING')
            score += 1.5
        
        # Détections avancées
        if event['segment'] == 'Premium' and score > 3:
            flags.append('VIP_ANOMALY')
            score += 2.0
        
        # Détection de patterns suspects
        hour = datetime.now().hour
        if event['service_type'] == 'VOICE' and 2 <= hour <= 5:
            flags.append('UNUSUAL_HOUR_ACTIVITY')
            score += 1.5
        
        # Détection de SIM box (plusieurs appels simultanés)
        sub_sessions = len([s for s in self.active_sessions.values() 
                           if s['subscriber']['subscriber_id'] == event['subscriber_id']])
        if sub_sessions > 3:
            flags.append('POSSIBLE_SIM_BOX')
            score += 4.0
        
        # Classification finale
        alert_level = "CRITICAL" if score > 7 else "ALERT" if score > 5 else "WARNING" if score > 2 else "OK"
        revenue_at_risk = score * 150.0 if event['segment'] == 'Premium' else score * 50.0
        congestion = "HIGH" if score > 5 else "MEDIUM" if score > 2 else "LOW"
        
        return flags, min(score, 10.0), alert_level, revenue_at_risk, congestion

    @processing_time_histogram.time()
    def _generate_streaming_event(self, subscriber: Dict, event_type: str, 
                                 session: Optional[Dict] = None) -> StreamingCDREvent:
        """Génère un événement CDR complet"""
        now = datetime.now()
        
        # Sélection de la tour cellulaire
        towers_in_city = [t for t in self.cell_towers if t['wilaya'] == subscriber['city']]
        tower = random.choice(towers_in_city if towers_in_city else self.cell_towers)
        
        # Gestion des sessions
        if event_type == 'SESSION_START' or not session:
            service_type = np.random.choice(
                ['VOICE', 'DATA', 'SMS', 'VoLTE', 'VoWiFi'],
                p=self.config.get('session_type_distribution', [0.2, 0.5, 0.15, 0.1, 0.05])
            )
            session_id = str(uuid.uuid4())
            session_state = 'INITIATING'
            duration = 0
            bytes_up = bytes_down = 0
        else:
            service_type = session['service_type']
            session_id = session['session_id']
            start_time = session['start_time']
            duration = int((now - start_time).total_seconds())
            
            if event_type == 'SESSION_UPDATE':
                session_state = 'ACTIVE'
                if service_type == 'DATA':
                    # Simulation réaliste du trafic data
                    app_cat = subscriber['top_app_category']
                    if app_cat == 'video':
                        rate = random.uniform(500, 2000)  # kbps
                    elif app_cat == 'social':
                        rate = random.uniform(50, 300)
                    else:
                        rate = random.uniform(100, 500)
                    
                    bytes_up = int(duration * rate * 0.15 * 128)  # 15% upload
                    bytes_down = int(duration * rate * 0.85 * 128)  # 85% download
                else:
                    bytes_up = bytes_down = 0
            else:  # SESSION_END
                session_state = 'COMPLETED'
                bytes_up = session.get('bytes_uploaded', 0)
                bytes_down = session.get('bytes_downloaded', 0)

        # Métriques QoS
        qos_metrics = self._generate_qos_metrics(tower['technology'])
        is_roaming = random.random() < self.config.get('prob_roaming', 0.04)
        roaming_partner = random.choice(["MAROC_TELECOM", "TUNISIE_TELECOM", "ORANGE_MALI"]) if is_roaming else None
        
        # Statistiques client
        cid = subscriber['subscriber_id']
        stat = self.customer_stats[cid]
        stat["distinct_cells"].add(tower['cell_id'])
        stat["sessions_last_24h"].append(now)
        stat["last_activity"] = now
        
        # Nettoyage des données anciennes
        cutoff_time = now - timedelta(hours=24)
        while stat["sessions_last_24h"] and stat["sessions_last_24h"][0] < cutoff_time:
            stat["sessions_last_24h"].popleft()
        
        # Calcul du data usage
        data_mb = (bytes_up + bytes_down) / 1024 / 1024
        stat["data_usage_rolling_mb"].append((now, data_mb))
        while stat["data_usage_rolling_mb"] and stat["data_usage_rolling_mb"][0][0] < cutoff_time:
            stat["data_usage_rolling_mb"].popleft()
        
        total_data_mb_24h = sum(v[1] for v in stat["data_usage_rolling_mb"])
        
        # Calcul des charges
        current_charge = self._calculate_charge(subscriber, service_type, duration, bytes_up + bytes_down)
        
        if event_type == "SESSION_END":
            stat["lifetime_value"] += current_charge
            stat["revenue_this_month"] += current_charge
        
        # Reset mensuel des revenus
        if now.day == 1 and now.hour < 2:
            stat["revenue_this_month"] = 0.0
        
        # Détection du risque de churn
        days_inactive = (now - stat["last_activity"]).days
        low_activity = len(stat["sessions_last_24h"]) < 2
        low_revenue = stat["revenue_this_month"] < 100
        churn_flag = int((days_inactive > 7) or (low_activity and low_revenue))
        
        # Détection d'anomalies
        event_data = {
            'service_type': service_type,
            'duration': duration,
            'data_volume': bytes_up + bytes_down,
            'latency': qos_metrics['latency'],
            'signal': qos_metrics['signal_strength'],
            'roaming': is_roaming,
            'segment': subscriber['segment'],
            'subscriber_id': cid
        }
        
        anomaly_flags, anomaly_score, qos_alert_level, revenue_at_risk, congestion_level = \
            self._detect_anomalies(event_data)

        # Construction de l'événement CDR
        return StreamingCDREvent(
            event_timestamp=now.isoformat(),
            ingestion_timestamp=(now + timedelta(milliseconds=random.randint(10, 100))).isoformat(),
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            subscriber_id=cid,
            msisdn=subscriber['msisdn'],
            imsi=subscriber['imsi'],
            imei=subscriber['imei'],
            session_id=session_id,
            service_type=service_type,
            session_state=session_state,
            cell_id=tower['cell_id'],
            lac=tower['lac'],
            mcc=tower['mcc'],
            mnc=tower['mnc'],
            wilaya=tower['wilaya'],
            network_type=tower['technology'],
            serving_node=self._select_serving_node(service_type),
            duration_seconds=duration,
            bytes_uploaded=bytes_up,
            bytes_downloaded=bytes_down,
            packets_lost=random.randint(0, 100) if service_type == 'DATA' else 0,
            latency_ms=qos_metrics['latency'],
            jitter_ms=qos_metrics['jitter'],
            qos_class='Premium' if subscriber['segment'] == 'Premium' else 'Standard',
            signal_strength_dbm=qos_metrics['signal_strength'],
            snr_db=qos_metrics['snr'],
            ber=qos_metrics['ber'],
            charging_state='ACTIVE' if event_type != 'SESSION_END' else 'COMPLETED',
            current_charge=current_charge,
            rate_plan_id=subscriber['rate_plan'],
            roaming_partner=roaming_partner,
            anomaly_flags=anomaly_flags,
            anomaly_score=anomaly_score,
            congestion_level=congestion_level,
            customer_segment=subscriber['segment'],
            customer_lifetime_value=stat["lifetime_value"],
            churn_risk_flag=churn_flag,
            revenue_this_month=stat["revenue_this_month"],
            num_distinct_cells_visited=len(stat["distinct_cells"]),
            top_app_category=subscriber['top_app_category'],
            revenue_at_risk=revenue_at_risk,
            qos_alert_level=qos_alert_level,
            is_roaming=int(is_roaming),
            sessions_last_24h=len(stat["sessions_last_24h"]),
            data_usage_rolling_mb=total_data_mb_24h,
            processing_node=f"cdr-gen-{self.hostname}-{random.randint(1,3)}"
        )

    def _select_serving_node(self, service_type: str) -> str:
        """Sélectionne le nœud réseau approprié"""
        if service_type in ['VOICE', 'VoLTE']:
            return random.choice(self.network_nodes['MSC'])
        elif service_type == 'DATA':
            return random.choice(self.network_nodes['SGSN'])
        elif service_type == 'VoWiFi':
            return random.choice(self.network_nodes['PGW'])
        else:
            return random.choice(self.network_nodes['MME'])

    def _generate_qos_metrics(self, technology: str) -> Dict:
        """Génère des métriques QoS réalistes selon la technologie"""
        qos_profiles = {
            '2G': {
                'latency': (80, 350),
                'jitter': (50, 150),
                'signal_strength': (-110, -85),
                'snr': (6, 15),
                'ber': (0.008, 0.1)
            },
            '3G': {
                'latency': (40, 130),
                'jitter': (15, 80),
                'signal_strength': (-105, -75),
                'snr': (10, 19),
                'ber': (0.001, 0.012)
            },
            '4G': {
                'latency': (15, 55),
                'jitter': (3, 20),
                'signal_strength': (-100, -65),
                'snr': (17, 32),
                'ber': (0.0001, 0.001)
            },
            '5G': {
                'latency': (2, 13),
                'jitter': (1, 8),
                'signal_strength': (-95, -62),
                'snr': (22, 44),
                'ber': (0.00001, 0.00009)
            }
        }
        
        profile = qos_profiles.get(technology, qos_profiles['4G'])
        
        # Ajout de variabilité pour simuler les conditions réseau
        congestion_factor = random.uniform(0.8, 1.5)
        
        return {
            'latency': random.uniform(*profile['latency']) * congestion_factor,
            'jitter': random.uniform(*profile['jitter']) * congestion_factor,
            'signal_strength': random.randint(*profile['signal_strength']),
            'snr': random.uniform(*profile['snr']),
            'ber': random.uniform(*profile['ber']) * congestion_factor
        }

    def _calculate_charge(self, subscriber: Dict, service_type: str, duration: int, data_volume: int) -> float:
        """Calcule les charges selon le plan tarifaire"""
        base_rates = {
            'VOICE': 2.5,    # DZD/minute
            'SMS': 5.0,      # DZD/SMS
            'DATA': 0.015,   # DZD/MB
            'VoLTE': 1.8,    # DZD/minute
            'VoWiFi': 1.5    # DZD/minute
        }
        
        segment_multipliers = {
            'Premium': 0.65,
            'Standard': 1.0,
            'Basic': 1.20,
            'Youth': 0.75
        }
        
        base_rate = base_rates.get(service_type, 1.0)
        multiplier = segment_multipliers.get(subscriber['segment'], 1.0)
        
        if service_type in ['VOICE', 'VoLTE', 'VoWiFi']:
            charge = (duration / 60.0) * base_rate * multiplier
        elif service_type == 'DATA':
            charge = (data_volume / (1024 * 1024)) * base_rate * multiplier
        else:  # SMS
            charge = base_rate * multiplier
        
        # Tarification spéciale week-end
        if datetime.now().weekday() >= 5 and subscriber['segment'] == 'Youth':
            charge *= 0.8
        
        return round(max(charge, 0.0), 2)

    @kafka_send_histogram.time()
    # def send_event(self, event: StreamingCDREvent, topic: str):
    #     """Envoie l'événement vers Kafka avec gestion d'erreurs"""
    #     try:
    #         event_dict = asdict(event)
    #         key = event.session_id  # Partitionnement par session
            
    #         logger.debug(f"Key type: {type(key)}, value: {key}")
    #         logger.debug(f"Event type fields: event_type={type(event.event_type)}, service_type={type(event.service_type)}")

    #         # Headers Kafka pour le routage et le monitoring
    #         headers = []
    #         header_data = [
    #             ('event_type', event.event_type),
    #             ('service_type', event.service_type),
    #             ('schema_version', event.schema_version),
    #             ('processing_node', event.processing_node),
    #             ('wilaya', event.wilaya)
    #         ]

    #         for header_name, header_value in header_data:
    #             if isinstance(header_value, str):
    #                 headers.append((header_name, header_value.encode('utf-8')))
    #             elif isinstance(header_value, bytes):
    #                 headers.append((header_name, header_value))
    #             else:
    #                 headers.append((header_name, str(header_value).encode('utf-8')))

    #                 # Vérification du key
    #             if isinstance(key, str):
    #                 key_bytes = key.encode('utf-8')
    #             elif isinstance(key, bytes):
    #                 key_bytes = key
    #             else:
    #                 key_bytes = str(key).encode('utf-8')
            
    #         # Callback pour gérer le résultat
    #         def on_send_success(record_metadata):
    #             self.metrics['events_sent'] += 1
    #             self.metrics[f'events_{topic}'] += 1
                
    #         def on_send_error(ex):
    #             logger.error(f"Failed to send to {topic}: {ex}")
    #             error_counter.labels(error_type='kafka_send').inc()
    #             self.metrics['send_errors'] += 1
            
    #         # Envoi asynchrone avec callbacks
    #         future = self.producer.send(
    #             topic=topic,
    #             key=key.encode() if isinstance(key, str) else key,
    #             value=event_dict,
    #             headers=headers,
    #             timestamp_ms=int(time.time() * 1000)
    #         )
            
    #         future.add_callback(on_send_success)
    #         future.add_errback(on_send_error)
            
    #         # Mise à jour des métriques
    #         event_counter.labels(event.event_type).inc()
    #         if event.anomaly_flags:
    #             anomaly_counter.inc()
    #         active_sessions_gauge.set(len(self.active_sessions))
            
    #     except KafkaError as e:
    #         logger.error(f"Kafka error sending event: {e}")
    #         error_counter.labels(error_type='kafka_send').inc()
    #         self.metrics['send_errors'] += 1
    #     except Exception as e:
    #         logger.error(f"Unexpected error sending event: {e}")
    #         error_counter.labels(error_type='unexpected').inc()
    #         self.metrics['send_errors'] += 1

    @kafka_send_histogram.time()
    def send_event(self, event: StreamingCDREvent, topic: str):
        """Envoie l'événement vers Kafka avec gestion d'erreurs"""
        try:
            event_dict = asdict(event)
            # S'assurer que tous les champs sont sérialisables
            # Convertir les listes en strings pour éviter les problèmes
            if 'anomaly_flags' in event_dict and isinstance(event_dict['anomaly_flags'], list):
                event_dict['anomaly_flags'] = (
                    ','.join(event_dict['anomaly_flags'])
                    if event_dict['anomaly_flags'] else ''
                )
            # Clé de partitionnement
            key = str(event.session_id)
            # Callback pour gérer le résultat
            def on_send_success(record_metadata):
                self.metrics['events_sent'] += 1
                self.metrics[f'events_{topic}'] += 1
                logger.debug(
                    f"Event sent successfully to {topic}, partition "
                    f"{record_metadata.partition}, offset {record_metadata.offset}"
                )
            def on_send_error(ex):
                logger.error(f"Failed to send to {topic}: {ex}")
                error_counter.labels(error_type='kafka_send').inc()
                self.metrics['send_errors'] += 1
            # Envoi simple sans headers pour éviter les problèmes d'encodage
            future = self.producer.send(
                topic=topic,
                key=key,
                value=event_dict
            )
            future.add_callback(on_send_success)
            future.add_errback(on_send_error)
            # Mise à jour des métriques
            event_counter.labels(event.event_type).inc()
            if hasattr(event, 'anomaly_flags') and event.anomaly_flags:
                anomaly_counter.inc()
            active_sessions_gauge.set(len(self.active_sessions))
        except Exception as e:
            logger.error(f"Unexpected error in send_event: {e}", exc_info=True)
            error_counter.labels(error_type='unexpected').inc()
            self.metrics['send_errors'] += 1

    def run_generator(self, events_per_second: int = 400):
        """Lance la génération d'événements en continu"""
        logger.info(f"🚀 Starting CDR stream generation at {events_per_second} events/sec")
        logger.info(f"📡 Connected to Kafka brokers: {self.kafka_config['bootstrap_servers']}")
        
        # Gestion des signaux pour arrêt propre
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Thread de reporting des métriques
        metrics_thread = threading.Thread(target=self._report_metrics, daemon=True)
        metrics_thread.start()
        
        # Thread de nettoyage périodique
        cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        cleanup_thread.start()
        
        # Configuration du batch processing
        batch_size = min(100, events_per_second // 10)
        sleep_interval = batch_size / events_per_second
        
        logger.info(f"📦 Batch size: {batch_size}, Sleep interval: {sleep_interval:.3f}s")
        
        events_generated = 0
        start_time = time.time()
        
        while self.running:
            try:
                batch_start = time.time()
                now = datetime.now()
                hour = now.hour
                day_of_week = now.weekday()
                
                for _ in range(batch_size):
                    # Sélection aléatoire d'un abonné
                    subscriber = random.choice(self.subscriber_pool)
                    
                    # Application du pattern d'activité
                    activity_mult = self._get_activity_multiplier(
                        hour, subscriber['activity_pattern'], day_of_week
                    )
                    
                    # Skip probabiliste selon l'activité
                    if random.random() > min(activity_mult, 1.0):
                        continue
                    
                    # Détermination du type d'événement
                    event_type_probs = self._get_event_type_probabilities()
                    event_type = np.random.choice(
                        ['SESSION_START', 'SESSION_UPDATE', 'SESSION_END'],
                        p=event_type_probs
                    )
                    
                    # Génération de l'événement
                    if event_type == 'SESSION_START':
                        event = self._generate_streaming_event(subscriber, event_type)
                        
                        # Stockage de la session active
                        self.active_sessions[event.session_id] = {
                            'subscriber': subscriber,
                            'start_time': now,
                            'service_type': event.service_type,
                            'session_id': event.session_id,
                            'bytes_uploaded': 0,
                            'bytes_downloaded': 0,
                            'cell_id': event.cell_id
                        }
                        
                        # Envoi vers les topics appropriés
                        self.send_event(event, 'cdr-session-events')
                        
                        # Envoi vers business KPI pour les nouvelles sessions
                        if random.random() < 0.1:  # 10% échantillonnage
                            self.send_event(event, 'cdr-business-kpi')
                        
                    elif event_type == 'SESSION_UPDATE' and self.active_sessions:
                        # Mise à jour d'une session existante
                        session_id = random.choice(list(self.active_sessions.keys()))
                        session = self.active_sessions[session_id]
                        
                        event = self._generate_streaming_event(
                            session['subscriber'], event_type, session
                        )
                        
                        # Mise à jour des données de session
                        session['bytes_uploaded'] = event.bytes_uploaded
                        session['bytes_downloaded'] = event.bytes_downloaded
                        
                        self.send_event(event, 'cdr-session-events')
                        
                    elif event_type == 'SESSION_END' and self.active_sessions:
                        # Fin d'une session
                        session_id = random.choice(list(self.active_sessions.keys()))
                        session = self.active_sessions.pop(session_id)
                        
                        event = self._generate_streaming_event(
                            session['subscriber'], event_type, session
                        )
                        
                        self.send_event(event, 'cdr-session-events')
                        
                        # Envoi enrichi pour les sessions terminées
                        if event.anomaly_score > 0:
                            self.send_event(event, 'cdr-session-enriched')
                    else:
                        continue
                    
                    # Envoi vers topics spécialisés selon les conditions
                    if event.anomaly_flags:
                        self.send_event(event, 'cdr-anomalies')
                    
                    if event.qos_alert_level in ["ALERT", "CRITICAL"]:
                        self.send_event(event, 'cdr-qos-metrics')
                    
                    events_generated += 1
                
                # Flush périodique du producer
                if events_generated % 1000 == 0:
                    self.producer.flush(timeout=1)
                
                # Calcul du temps de traitement et ajustement
                batch_duration = time.time() - batch_start
                adjusted_sleep = max(0, sleep_interval - batch_duration)
                
                if adjusted_sleep > 0:
                    time.sleep(adjusted_sleep)
                else:
                    logger.warning(f"⚠️ Cannot maintain {events_per_second} events/sec rate")
                
            except Exception as e:
                logger.error(f"Error in generation loop: {e}", exc_info=True)
                error_counter.labels(error_type='generation_loop').inc()
                self.metrics['generation_errors'] += 1
                time.sleep(1)  # Pause avant retry

    def _get_event_type_probabilities(self) -> List[float]:
        """Calcule les probabilités des types d'événements selon l'état"""
        total_sessions = len(self.active_sessions)
        
        if total_sessions < 100:
            # Peu de sessions actives, favoriser les démarrages
            return [0.50, 0.40, 0.10]
        elif total_sessions > 5000:
            # Beaucoup de sessions, favoriser les fins
            return [0.10, 0.50, 0.40]
        else:
            # État normal
            return [0.30, 0.55, 0.15]

    def _periodic_cleanup(self):
        """Nettoyage périodique des sessions obsolètes et des statistiques"""
        while self.running:
            try:
                time.sleep(300)  # Toutes les 5 minutes
                
                # Nettoyage des sessions obsolètes
                self._cleanup_stale_sessions()
                
                # Nettoyage des statistiques clients inactifs
                self._cleanup_inactive_customers()
                
                # Garbage collection forcé si nécessaire
                if len(self.customer_stats) > 50000:
                    import gc
                    gc.collect()
                    logger.info("🧹 Forced garbage collection completed")
                    
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                error_counter.labels(error_type='cleanup').inc()

    def _cleanup_stale_sessions(self):
        """Nettoie les sessions qui durent trop longtemps"""
        now = datetime.now()
        stale_threshold = timedelta(hours=4)  # Sessions > 4h considérées comme obsolètes
        sessions_to_remove = []
        
        for session_id, session in self.active_sessions.items():
            if now - session['start_time'] > stale_threshold:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            session = self.active_sessions.pop(session_id)
            logger.info(f"🧹 Cleaned stale session: {session_id} (duration: {now - session['start_time']})")
            
            # Générer un événement de fin forcé
            event = self._generate_streaming_event(
                session['subscriber'], 'SESSION_END', session
            )
            if not isinstance(event.anomaly_flags, list):
                event.anomaly_flags = []
            event.anomaly_flags.append('STALE_SESSION_CLEANED')
            self.send_event(event, 'cdr-session-events')
            self.send_event(event, 'cdr-anomalies')
        
        if sessions_to_remove:
            self.metrics['stale_sessions_cleaned'] += len(sessions_to_remove)
            logger.info(f"🧹 Cleaned {len(sessions_to_remove)} stale sessions")

    def _cleanup_inactive_customers(self):
        """Nettoie les statistiques des clients inactifs"""
        now = datetime.now()
        inactive_threshold = timedelta(days=30)
        customers_to_remove = []
        
        for customer_id, stats in self.customer_stats.items():
            if now - stats['last_activity'] > inactive_threshold:
                customers_to_remove.append(customer_id)
        
        for customer_id in customers_to_remove:
            del self.customer_stats[customer_id]
        
        if customers_to_remove:
            logger.info(f"🧹 Removed stats for {len(customers_to_remove)} inactive customers")

    def _report_metrics(self):
        """Rapporte périodiquement les métriques"""
        while self.running:
            time.sleep(30)  # Rapport toutes les 30 secondes
            
            try:
                runtime = time.time() - self.start_time if hasattr(self, 'start_time') else 0
                events_per_sec = self.metrics['events_sent'] / max(runtime, 1)
                
                logger.info("📊 Generator Metrics:")
                logger.info(f"  ⏱️  Runtime: {runtime:.0f}s")
                logger.info(f"  📈 Events sent: {self.metrics['events_sent']:,}")
                logger.info(f"  ⚡ Rate: {events_per_sec:.1f} events/sec")
                logger.info(f"  🔄 Active sessions: {len(self.active_sessions):,}")
                logger.info(f"  👥 Tracked customers: {len(self.customer_stats):,}")
                logger.info(f"  ❌ Send errors: {self.metrics['send_errors']:,}")
                logger.info(f"  ⚠️  Generation errors: {self.metrics['generation_errors']:,}")
                logger.info(f"  🧹 Stale sessions cleaned: {self.metrics.get('stale_sessions_cleaned', 0):,}")
                
                # Métriques par topic
                logger.info("  📊 Events by topic:")
                for topic in ['cdr-session-events', 'cdr-anomalies', 'cdr-qos-metrics', 
                             'cdr-business-kpi', 'cdr-session-enriched']:
                    count = self.metrics.get(f'events_{topic}', 0)
                    if count > 0:
                        logger.info(f"    - {topic}: {count:,}")
                
                # État de santé
                error_rate = self.metrics['send_errors'] / max(self.metrics['events_sent'], 1)
                if error_rate > 0.01:
                    logger.warning(f"⚠️  High error rate: {error_rate:.2%}")
                
            except Exception as e:
                logger.error(f"Error reporting metrics: {e}")

    def _signal_handler(self, signum, frame):
        """Gestion propre de l'arrêt"""
        logger.info("🛑 Shutdown signal received, stopping generator gracefully...")
        self.running = False
        
        # Flush final des événements
        try:
            self.producer.flush(timeout=5)
            logger.info("✅ Final flush completed")
        except Exception as e:
            logger.error(f"Error during final flush: {e}")
        
        # Fermeture du producer
        self.producer.close()
        
        # Rapport final
        logger.info("📊 Final Statistics:")
        logger.info(f"  - Total events sent: {self.metrics['events_sent']:,}")
        logger.info(f"  - Total errors: {self.metrics['send_errors']:,}")
        logger.info(f"  - Active sessions at shutdown: {len(self.active_sessions):,}")
        
        sys.exit(0)


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Algérie Télécom CDR Stream Generator - Production Version'
    )
    parser.add_argument('--rate', type=int, default=400,
                       help='Events per second to generate (default: 400)')
    parser.add_argument('--brokers', nargs='+', 
                       default=['broker1:9092', 'broker2:9093', 'broker3:9094'],
                       help='Kafka broker addresses')
    parser.add_argument('--config', type=str, required=True,
                       help='Path to configuration JSON file')
    parser.add_argument('--ramadan-mode', action='store_true',
                       help='Enable Ramadan traffic patterns')
    
    args = parser.parse_args()
    
    # Chargement de la configuration
    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"❌ Failed to load config file: {e}")
        sys.exit(1)
    
    # Override avec les arguments CLI
    config['kafka_brokers'] = args.brokers
    config['events_per_second'] = args.rate
    config['ramadan_mode'] = args.ramadan_mode
    
    # Création et lancement du générateur
    generator = StreamingCDRGenerator(config)
    generator.start_time = time.time()
    
    try:
        logger.info("🚀 Algérie Télécom CDR Streaming Generator v2.0")
        logger.info("=" * 50)
        generator.run_generator(events_per_second=args.rate)
    except KeyboardInterrupt:
        logger.info("⏹️  Generator stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise
    finally:
        if hasattr(generator, 'producer'):
            generator.producer.close()
        logger.info("👋 Generator shutdown complete")


if __name__ == "__main__":
    main()