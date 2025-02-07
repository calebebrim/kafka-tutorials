from producers import create_kafka_producer, send_message, get_schema_from_registry
from google.protobuf import message
import example_pb2  # Generated protobuf file
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCHEMA = get_schema_from_registry("protobuf_topic")

def protobuf_producer():
    """Creates and sends a Protobuf message to Kafka."""
    producer = create_kafka_producer()

    # Assuming `example_pb2` contains the Protobuf message definition
    message = example_pb2.YourMessageType()
    message.field1 = "value1"
    message.field2 = "value2"

    producer.send("protobuf_topic", value=message.SerializeToString())
    producer.flush()

    send_message(producer, message)
    logger.info(f"Protobuf message sent: {message}")

if __name__ == "__main__":
    protobuf_producer()
