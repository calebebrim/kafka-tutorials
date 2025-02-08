from producers import create_kafka_producer, send_message
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def json_producer():
    """Creates and sends a JSON message to Kafka."""
    producer = create_kafka_producer()

    message = {
        "field1": "value1",
        "field2": "value2"
    }

    producer.send("json_topic", value=message)
    producer.flush()

    send_message(producer, message)
    logger.info(f"JSON message sent: {message}")

if __name__ == "__main__":
    json_producer()
