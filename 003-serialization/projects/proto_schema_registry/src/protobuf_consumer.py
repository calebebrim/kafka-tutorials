import os
import logging
from threading import Thread
from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient, NewTopic

# Configure logger
logging.basicConfig(level=logging.INFO)
kafka_consumer_logger = logging.getLogger("kafka_consumer")

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
SCHEMA_TOPIC = os.getenv('SCHEMA_TOPIC', 'protobuf_schema_topic')
GROUP_ID = os.getenv('GROUP_ID', 'protobuf_schema_registry_group')

class ProtobufConsumer:
    def __init__(self):
        self._ensure_topic_exists()
        
        self._consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': GROUP_ID,
            'auto.offset.reset': 'earliest'
        })
        self._cancelled = False
        self._subscriber = None  # Holds the subscribed function
        self._reset_offsets()
        
        self._thread = Thread(target=self._consume_loop)
        kafka_consumer_logger.info("Starting KafkaConsumer main thread.")
        self._thread.daemon = True
        self._thread.start()
        kafka_consumer_logger.info("KafkaConsumer main thread started.")

    def _ensure_topic_exists(self):
        kafka_consumer_logger.info(f"Checking if topic '{SCHEMA_TOPIC}' exists...")
        admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
        topic_metadata = admin_client.list_topics(timeout=10)

        if SCHEMA_TOPIC not in topic_metadata.topics:
            kafka_consumer_logger.info(f"Topic '{SCHEMA_TOPIC}' not found. Creating it now...")
            new_topic = NewTopic(SCHEMA_TOPIC, num_partitions=1, replication_factor=1)
            future = admin_client.create_topics([new_topic])
            for topic, f in future.items():
                try:
                    f.result()  # Wait for the topic creation to complete
                    kafka_consumer_logger.info(f"Topic '{SCHEMA_TOPIC}' created successfully.")
                except Exception as e:
                    kafka_consumer_logger.error(f"Failed to create topic '{SCHEMA_TOPIC}': {e}")
        else:
            kafka_consumer_logger.info(f"Topic '{SCHEMA_TOPIC}' already exists.")

    def _reset_offsets(self):
        kafka_consumer_logger.info("Resetting consumer group offsets to earliest...")
        admin_client = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
        partitions = {SCHEMA_TOPIC: [0]}  # Modify if multiple partitions exist
        
        try:
            future = admin_client.alter_consumer_group_offsets(GROUP_ID, partitions)
            for topic_partition, f in future.items():
                f.result()  # Wait for the offset reset to complete
            kafka_consumer_logger.info("Consumer group offsets successfully reset to earliest.")
        except Exception as e:
            kafka_consumer_logger.error(f"Failed to reset consumer offsets: {e}")

    def subscribe(self, callback):
        """Subscribe a function to be called when a new message is received."""
        self._subscriber = callback

    def _consume_loop(self):
        kafka_consumer_logger.info(f"Starting to consume from topic: {SCHEMA_TOPIC}")
        self._consumer.subscribe([SCHEMA_TOPIC])

        while not self._cancelled:
            msg = self._consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                kafka_consumer_logger.error(f"Consumer error: {msg.error()}")
                continue
            
            schema_id = msg.key().decode('utf-8') if msg.key() else None
            schema = msg.value().decode('utf-8') if msg.value() else None
            kafka_consumer_logger.info(f"Received message: key={schema_id}, value={schema}")
            self._process_message(schema_id, schema)

    def _process_message(self, schema_id, schema):
        kafka_consumer_logger.info(f"Processing schema_id: {schema_id}")
        if self._subscriber:
            self._subscriber(schema_id, schema)

    def close(self):
        self._cancelled = True
        self._thread.join()
        self._consumer.close()
        kafka_consumer_logger.info("KafkaConsumer closed")
