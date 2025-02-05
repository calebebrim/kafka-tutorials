from confluent_kafka import Consumer
import fastavro
import json
from google.protobuf import message
import example_pb2  # Replace with your generated Protobuf class
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
import requests
import io

# Kafka Configuration
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'consumer-group',
    'auto.offset.reset': 'earliest'
}
consumer = Consumer(conf)

# Avro Schema Registry Client
schema_registry_url = 'http://localhost:8081'  # Confluent Schema Registry URL
schema_registry_client = SchemaRegistryClient({'url': schema_registry_url})

# Protobuf Schema Registry Client (for Buf)
buf_schema_registry_url = 'http://localhost:8082'  # Buf Schema Registry URL
buf_client = BufClient()  # Configure Buf Schema Registry client

# Avro Deserialization
def avro_deserializer(serialized_data, schema_name):
    schema = schema_registry_client.get_schema(schema_name)
    avro_deserializer = AvroDeserializer(schema, schema_registry_client)
    return avro_deserializer(serialized_data)

# Protobuf Deserialization
def protobuf_deserializer(serialized_data):
    user = example_pb2.User()
    user.ParseFromString(serialized_data)
    return {"name": user.name, "age": user.age}

# JSON Deserialization
def json_deserializer(serialized_data):
    return json.loads(serialized_data.decode('utf-8'))

# Heuristic to detect if the data is in JSON format
def is_json(data):
    try:
        json.loads(data)
        return True
    except (ValueError, TypeError):
        return False

# Heuristic to detect if the data is in Avro format
def is_avro(data):
    try:
        reader = fastavro.reader(io.BytesIO(data))
        return True
    except Exception:
        return False

# Heuristic to detect if the data is in Protobuf format
def is_protobuf(data):
    try:
        user = example_pb2.User()
        user.ParseFromString(data)
        return True
    except message.DecodeError:
        return False

# Automatically detect the format of the data
def detect_format(data):
    if is_json(data):
        return 'json'
    elif is_avro(data):
        return 'avro'
    elif is_protobuf(data):
        return 'protobuf'
    else:
        return None  # Unknown format

# Deserialize message based on detected format and headers
def deserialize_message(serialized_data, headers):
    registry_path = headers.get('registry-path')
    
    # Determine the format
    format = detect_format(serialized_data)
    
    if format == 'avro':
        # Use registry path from the header to get schema name
        schema_name = registry_path.decode('utf-8').split('/')[-1]
        return avro_deserializer(serialized_data, schema_name)
    elif format == 'protobuf':
        return protobuf_deserializer(serialized_data)
    elif format == 'json':
        return json_deserializer(serialized_data)
    else:
        raise ValueError("Unknown format")

# Consume message from Kafka with schema info in headers
def consume_message(topic):
    consumer.subscribe([topic])
    msg = consumer.poll(1.0)
    if msg is None:
        print("No message received")
    elif msg.error():
        print(f"Error: {msg.error()}")
    else:
        print(f"Consumed message: {deserialize_message(msg.value(), msg.headers())}")

# Example usage
consume_message('user-topic')
