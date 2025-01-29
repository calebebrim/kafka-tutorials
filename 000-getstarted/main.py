from confluent_kafka import Producer, Consumer, KafkaException
import json
import time

# Kafka Configuration
KAFKA_BROKER = 'localhost:9092'
TOPIC = 'example_topic'
CONSUMER_TIMEOUT = 10  # Timeout in seconds

# Producer
def produce_messages():
    producer = Producer({'bootstrap.servers': KAFKA_BROKER})

    for i in range(5):
        message = {'id': i, 'value': f'Hello Kafka {i}'}
        producer.produce(TOPIC, key=str(i), value=json.dumps(message))
        print(f"Produced: {message}")
        producer.flush()  # Ensures messages are delivered

    producer.flush()

# Consumer with timeout
def consume_messages(timeout=CONSUMER_TIMEOUT):
    consumer = Consumer({
        'bootstrap.servers': KAFKA_BROKER,
        'group.id': 'example_group',
        'auto.offset.reset': 'earliest'
    })

    consumer.subscribe([TOPIC])

    print("Consuming messages...")
    start_time = time.time()

    try:
        while time.time() - start_time < timeout:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())

            print(f"Consumed: {json.loads(msg.value().decode('utf-8'))}")

    except KeyboardInterrupt:
        print("\nShutting down consumer...")

    finally:
        consumer.close()
        print("Consumer stopped after timeout.")

if __name__ == "__main__":
    produce_messages()
    time.sleep(2)  # Wait for Kafka to process messages
    consume_messages()
