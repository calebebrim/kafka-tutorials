# file located at: src/utils/memory_manager.py

import logging
from threading import Lock
from typing import Dict, Optional, List
from protobuf_producer import ProtobufProducer 
from protobuf_consumer import ProtobufConsumer
from schemas import ProtobufSchema

# Configure logger
memory_logger = logging.getLogger("protobuf_memory")

class ProtobufMemory:
    def __init__(self) -> None:
        """Initialize an in-memory schema storage with thread safety and integrate with Kafka consumer and producer."""
        self._schemas: Dict[str, Dict[str, Dict[int, ProtobufSchema]]] = {}
        self._lock: Lock = Lock()
        self._consumer: ProtobufConsumer = ProtobufConsumer()
        self._producer: ProtobufProducer = ProtobufProducer()
        self._consumer.subscribe(self._process_message)
        memory_logger.info(
            "Initialized ProtobufMemory storage with Kafka integration.")

    def _process_message(self, schema_id: str, text_schema: str) -> None:
        """Process incoming Kafka messages and store them in memory."""
        memory_logger.info(
            f"Processing schema_id: {schema_id} from Kafka message.")
        schema = ProtobufSchema.deserialize_from_text(text_schema)
        self.add_schema(schema)

    def add_schema(self, schema: ProtobufSchema) -> int:
        """Add or update a schema in memory and produce it to Kafka."""
        with self._lock:
            schema_id: str = schema.schema_id
            if schema_id not in self._schemas:
                self._schemas[schema_id] = {"latest_version": 0, "schemas": {}}
            latest_version: int = self._schemas[schema_id]["latest_version"] + 1
            self._schemas[schema_id]["schemas"][latest_version] = schema
            self._schemas[schema_id]["latest_version"] = latest_version

        memory_logger.info(f"Schema {schema_id} stored at version {latest_version}.")

        # Produce the schema to Kafka
        self._producer.produce(schema_id, schema.serialize_to_text())
        return latest_version

    def get_schema(self, schema_id: str, version: Optional[int] = None) -> Optional[ProtobufSchema]:
        """Retrieve a schema by ID and optionally a specific version."""
        memory_logger.info(f"Retrieving schema {schema_id}:{version}")
        memory_logger.info(f"Schemas: {self._schemas}")

        with self._lock:
            if schema_id not in self._schemas:
                return None
            if version is None:
                memory_logger.debug(self._schemas[schema_id])
                version = self._schemas[schema_id]["latest_version"]
                memory_logger.info(f"Found a schema version for {schema_id}: {version}")
            schema = self._schemas[schema_id]["schemas"].get(version)
            memory_logger.debug(f"Schema: {schema.serialize_to_text() if schema else 'None'}")
            return schema

    def delete_schema(self, schema_id: str) -> bool:
        """Remove a schema from memory."""
        with self._lock:
            if schema_id in self._schemas:
                del self._schemas[schema_id]
                memory_logger.info(f"Schema {schema_id} deleted from memory.")
                return True
            return False

    def list_schemas(self) -> List[str]:
        """List all stored schema IDs."""
        with self._lock:
            return list(self._schemas.keys())

    def clear_all(self) -> None:
        """Clear all schemas from memory."""
        with self._lock:
            self._schemas.clear()
        memory_logger.info("All schemas cleared from memory.")

    def close(self) -> None:
        """Close the consumer and producer connections."""
        self._consumer.close()
        self._producer.close()
        memory_logger.info("ProtobufMemory shutdown complete.")
