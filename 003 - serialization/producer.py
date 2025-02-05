from confluent_kafka import Producer
import fastavro
import json
from google.protobuf import message
import example_pb2  # Replace with your generated Protobuf class
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
import requests
import io

# Kafka Configuration
conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'producer'
}
producer = Producer(conf)

# Avro Schema Registry Client
schema_registry_url = 'http://localhost:8081'  # Confluent Schema Registry URL
schema_registry_client = SchemaRegistryClient({'url': schema_registry_url})

# Protobuf Schema Registry Client (for Buf)
buf_schema_registry_url = 'http://localhost:8082'  # Buf Schema Registry URL
buf_client = BufClient()  # Configure Buf Schema Registry client

# Avro Serialization
def avro_serializer(value, schema_name):
    schema = schema_registry_client.get_schema(schema_name)
    avro_serializer = AvroSerializer(schema, schema_registry_client)
    return avro_serializer(value)

# Protobuf Serialization
def protobuf_serializer(value):
    user = example_pb2.User(name=value['name'], age=value['age'])
    return user.SerializeToString()

# JSON Serialization
def json_serializer(value):
    return json.dumps(value).encode('utf-8')

# Produce message to Kafka with schema info in headers
def produce_message(topic, value, format='json', schema_name=None, registry_path=None):
    headers = {}
    if registry_path:
        headers['registry-path'] = registry_path.encode('utf-8')  # Add registry path in headers
    
    # Serialize the value based on the selected format
    if format == 'avro':
        serialized_value = avro_serializer(value, schema_name)
    elif format == 'protobuf':
        serialized_value = protobuf_serializer(value)
    else:
        serialized_value = json_serializer(value)

    producer.produce(topic, value=serialized_value, headers=headers)
    producer.flush()

# Example Avro format
avro_message = {"name": "John", "age": 30}
avro_schema_name = "user-avro-schema"  # Example Avro schema name in the registry
avro_registry_path = "http://localhost:8081/avro/user-avro-schema"
produce_message('user-topic', avro_message, format='avro', schema_name=avro_schema_name, registry_path=avro_registry_path)

# Example Protobuf format
protobuf_message = {"name": "Alice", "age": 25}
# Assuming we have a Protobuf schema defined in Buf with the `User` message type
protobuf_registry_path = "http://localhost:8082/protobuf/user-protobuf-schema"
produce_message('user-topic', protobuf_message, format='protobuf', registry_path=protobuf_registry_path)

# Example JSON format
json_message = {"name": "Bob", "age": 40}
produce_message('user-topic', json_message, format='json', registry_path=None)

print("Messages produced to Kafka!")
