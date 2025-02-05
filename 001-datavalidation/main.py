from confluent_kafka import Producer, Consumer, KafkaException
import json
from collections import defaultdict
import threading
import time

KAFKA_CONFIG_CONSUMER = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'message-processing',
    'auto.offset.reset': 'earliest'
}

KAFKA_CONFIG_PRODUCER = {
    'bootstrap.servers': 'localhost:9092'
}

def produce_messages(producer, topic, messages):
    """Produces a batch of messages to the specified Kafka topic."""
    for msg in messages:
        print(f"[producing_messages] Producing message to {topic}: {msg}")
        producer.produce(topic, key=msg['id'], value=json.dumps(msg))
    producer.flush()
    print(f"[producing_messages] Finished producing {len(messages)} messages to {topic}")

def validate_message(msg):
    """Validates the incoming message structure and fields."""
    try:
        if not msg:
            raise ValueError("Empty message received")
        data = json.loads(msg)
        if 'id' not in data or 'value' not in data:
            raise ValueError("Missing required fields: 'id' or 'value'")
        return True, data
    except Exception as e:
        print(f"[validating_messages] Validation failed: {e}")
        return False, str(e)

def process_bronze(stop_event):
    """Processes raw messages from the Bronze topic, validating them."""
    consumer = Consumer(KAFKA_CONFIG_CONSUMER)
    producer = Producer(KAFKA_CONFIG_PRODUCER)
    consumer.subscribe(['bronze'])
    print("[validating_messages] Bronze processor started.")

    while not stop_event.is_set():
        msg = consumer.poll(1.0)
        if msg is None or msg.value() is None:
            continue
        if msg.error():
            print(f"[validating_messages] Consumer error: {msg.error()}")
            continue

        valid, data = validate_message(msg.value().decode('utf-8'))
        if valid:
            print(f"[validating_messages] Message validated: {data}")
            producer.produce('silver', key=data['id'], value=json.dumps(data))
        else:
            print(f"[validating_messages] Message validation failed. Moving to error topic: {data}")
            error_data = {'original': msg.value().decode('utf-8'), 'error': data}
            producer.produce('bronze_validation_failed_message', value=json.dumps(error_data))
        producer.flush()
    print("[validating_messages] Bronze processor shutting down.")

def attempt_message_fix(stop_event):
    """Attempts to fix messages in the failed validation topic."""
    consumer = Consumer(KAFKA_CONFIG_CONSUMER)
    producer = Producer(KAFKA_CONFIG_PRODUCER)
    consumer.subscribe(['bronze_validation_failed_message'])
    print("[fixing_messages] Error handler started.")

    while not stop_event.is_set():
        msg = consumer.poll(1.0)
        if msg is None or msg.value() is None:
            continue

        try:
            data = json.loads(msg.value().decode('utf-8'))
            original_data = json.loads(data['original'])
            error = data['error']
        except json.JSONDecodeError:
            print("[fixing_messages] Skipping invalid JSON message in error topic")
            continue

        print(f"[fixing_messages] Attempting to fix message: {original_data}")
        if "Missing required fields" in error:
            if 'id' in original_data:
                if 'value' not in original_data:
                    original_data['value'] = "category" + str(int(original_data['id']) % 3)
                    print("[fixing_messages] Fixed missing 'value' field, sending to silver topic.")
                    producer.produce('silver', key=original_data['id'], value=json.dumps(original_data))
                    continue

            print("[fixing_messages] Message could not be fixed, sending to dead letter queue.")
            producer.produce('bronze_dead_messages', value=json.dumps(original_data))
        producer.flush()
    print("[fixing_messages] Error handler shutting down.")

def process_silver(stop_event):
    """Aggregates messages from the Silver topic and updates metrics."""
    consumer = Consumer(KAFKA_CONFIG_CONSUMER)
    producer = Producer(KAFKA_CONFIG_PRODUCER)
    consumer.subscribe(['silver'])
    group_counts = {}
    print("[aggregating_messages] Silver processor started.")

    while not stop_event.is_set():
        msg = consumer.poll(1.0)
        if msg is None or msg.value() is None:
            continue

        try:
            data = json.loads(msg.value().decode('utf-8'))
        except json.JSONDecodeError:
            print("[aggregating_messages] Skipping invalid JSON message in silver topic")
            continue

        group_key = data.get('value', 'unknown')
        if group_key not in group_counts:
            group_counts[group_key] = {}
            group_counts[group_key]["count"] = 0
            group_counts[group_key]["group_name"] = group_key
            group_counts[group_key]["ids"] = set([])

        group_counts[group_key]["count"] += 1
        group_counts[group_key]["ids"].add( data.get("id",-1))
        print(f"[aggregating_messages] Updated group count for {group_key}: {group_counts[group_key]}")

        producer.produce(f'gold_group_by_value', key=group_key, value=str(group_counts[group_key]))
        producer.flush()
    print("[aggregating_messages] Silver processor shutting down.")

# Producing test messages with failures
producer = Producer(KAFKA_CONFIG_PRODUCER)
test_messages = [{"id": str(i), "value": "category" + str(i % 3)} if i % 2 == 0 else {"id": str(i)} for i in range(10)]
print("[producing_messages] Producing test messages to Bronze topic...")
produce_messages(producer, 'bronze', test_messages)

# Running processing steps
stop_event = threading.Event()
bronze_thread = threading.Thread(target=process_bronze, args=(stop_event,), daemon=True)
fix_thread = threading.Thread(target=attempt_message_fix, args=(stop_event,), daemon=True)
silver_thread = threading.Thread(target=process_silver, args=(stop_event,), daemon=True)

bronze_thread.start()
fix_thread.start()
silver_thread.start()

time.sleep(60)
stop_event.set()
bronze_thread.join()
fix_thread.join()
silver_thread.join()
print("[main] Processing complete.")