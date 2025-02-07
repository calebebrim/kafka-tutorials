import logging
import os
from flask import Flask, request, jsonify
from producers import create_kafka_producer, get_schema_from_registry
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Environment variables
kafka_brokers = os.getenv('KAFKA_BROKERS', 'localhost:9093')
schema_registry_url = os.getenv('SCHEMA_REGISTRY_URL', 'http://localhost:8081')

# Initialize Kafka producer
producer = create_kafka_producer(kafka_brokers)

# Initialize Schema Registry client
schema_registry_conf = {"url": schema_registry_url}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

@app.route("/<topic>/produce", methods=["POST"])
def produce_message(topic):
    try:
        # Get JSON message from request body
        message = request.get_json()
        if not message:
            return jsonify({"error": "Invalid JSON payload"}), 400

        # Get Avro schema from Schema Registry
        schema_str = get_schema_from_registry(topic, message, schema_registry=schema_registry_url)
        if not schema_str:
            return jsonify({"error": f"Schema not found for topic: {topic}"}), 400

        # Create Avro serializer
        avro_serializer = AvroSerializer(schema_registry_client, schema_str)

        # Serialize message using Avro serializer
        value_serialized = avro_serializer(message, SerializationContext(topic, MessageField.VALUE))
        
        # Produce Avro message using Kafka producer
        producer.produce(topic=topic, key="key1", value=value_serialized)
        producer.flush()

        logger.info(f"Avro message sent: {message} to {topic}")
        return jsonify({"message": "Message sent successfully", "topic": topic}), 200
    except Exception as e:
        logger.error(f"Error producing message: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
