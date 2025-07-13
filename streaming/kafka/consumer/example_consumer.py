from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'cdr-session-events',
    bootstrap_servers=['127.0.0.1:9092', '127.0.0.1:9093', '127.0.0.1:9094'],
    auto_offset_reset='latest',
    group_id='debug-consumer',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
)

for message in consumer:
    print(message.value)
