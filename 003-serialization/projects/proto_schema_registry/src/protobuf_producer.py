import asyncio
import os
import logging
from threading import Thread
from confluent_kafka import Producer, KafkaException
from typing import Optional

# Configure logger
producer_logger: logging.Logger = logging.getLogger("protobuf_producer")

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
SCHEMA_TOPIC: str = os.getenv('SCHEMA_TOPIC', 'protobuf_schema_topic')

class ProtobufProducer:
    def __init__(self) -> None:
        """Initialize the Kafka producer for Protobuf messages."""
        self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._producer: Producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
        self._cancelled: bool = False
        
        self._poll_thread: Thread = Thread(target=self._poll_loop)
        self._poll_thread.start()
        producer_logger.info("ProtobufProducer initialized.")

    def _poll_loop(self) -> None:
        """Continuously poll Kafka to handle message delivery callbacks."""
        while not self._cancelled:
            self._producer.poll(0.1)

    async def produce(self, key: str, value: str) -> None:
        """Produce a Protobuf message to Kafka using a string key and string value."""
        result: asyncio.Future = self._loop.create_future()
        
        def ack(err: Optional[KafkaException], msg: Optional[Producer]) -> None:
            if err:
                self._loop.call_soon_threadsafe(result.set_exception, KafkaException(err))
            else:
                self._loop.call_soon_threadsafe(result.set_result, msg)
        
        self._producer.produce(SCHEMA_TOPIC, key=key.encode('utf-8'), value=value.encode('utf-8'), on_delivery=ack)
        producer_logger.info(f"Produced message to {SCHEMA_TOPIC} with key={key}")
        await result

    def close(self) -> None:
        """Close the Kafka producer safely."""
        self._cancelled = True
        self._poll_thread.join()
        producer_logger.info("ProtobufProducer closed.")
