import asyncio
import os
from threading import Thread
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from confluent_kafka import Producer, Consumer, KafkaException
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

app = FastAPI()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
SCHEMA_TOPIC = os.getenv('SCHEMA_TOPIC', 'protobuf_schema_topic')
GROUP_ID = os.getenv('GROUP_ID', 'protobuf_schema_registry_group')

# In-memory storage for schemas (replace with persistent storage in production)
schemas = {}

# Function to generate Protobuf classes dynamically in Python


def generate_protobuf(schema_id, schema_proto):
    file_descriptor_proto = descriptor_pb2.FileDescriptorProto()

    # Parse the `.proto` file definition as a plain string
    file_descriptor_proto.name = f"{schema_id}.proto"
    file_descriptor_proto.syntax = "proto3"
    file_descriptor_proto.message_type.add(name=schema_id)

    pool = descriptor_pool.Default()
    file_descriptor = pool.Add(file_descriptor_proto)

    factory = message_factory.MessageFactory()
    message_class = factory.GetPrototype(
        file_descriptor.message_types_by_name.get(schema_id))

    if not message_class:
        raise ValueError(f"Message type '{schema_id}' not found in schema.")

    return message_class


class KafkaProducer:
    def __init__(self, configs, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._producer = Producer(configs)
        self._cancelled = False
        self._poll_thread = Thread(target=self._poll_loop)
        self._poll_thread.start()

    def _poll_loop(self):
        while not self._cancelled:
            self._producer.poll(0.1)

    def close(self):
        self._cancelled = True
        self._poll_thread.join()

    async def produce(self, topic, key, value):
        result = self._loop.create_future()

        def ack(err, msg):
            if err:
                self._loop.call_soon_threadsafe(
                    result.set_exception, KafkaException(err))
            else:
                self._loop.call_soon_threadsafe(result.set_result, msg)

        self._producer.produce(topic, key=key, value=value, on_delivery=ack)
        return await result


class SchemaRequest(BaseModel):
    schema_id: str
    schema: str


@app.post("/schemas/")
async def create_schema(request: SchemaRequest):
    schema_id = request.schema_id
    schema = request.schema

    if schema_id in schemas:
        schemas[schema_id].append(schema)
    else:
        schemas[schema_id] = [schema]

    module = generate_protobuf(schema_id, schema)

    await app.state.producer.produce(
        SCHEMA_TOPIC,
        key=schema_id.encode('utf-8'),
        value=schema.encode('utf-8')
    )
    return {"schema_id": schema_id, "version": len(schemas[schema_id])}


@app.get("/schemas/{schema_id}")
async def read_schema(schema_id: str, version: int = None):
    if schema_id not in schemas:
        raise HTTPException(status_code=404, detail="Schema not found")
    if version is None:
        return {"schema": schemas[schema_id][-1], "version": len(schemas[schema_id])}
    if version > len(schemas[schema_id]) or version < 1:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"schema": schemas[schema_id][version - 1], "version": version}


@app.delete("/schemas/{schema_id}")
async def delete_schema(schema_id: str):
    if schema_id not in schemas:
        raise HTTPException(status_code=404, detail="Schema not found")
    del schemas[schema_id]
    return {"message": f"Schema {schema_id} deleted successfully"}


@app.delete("/schemas/")
async def delete_all_schemas():
    schemas.clear()
    return {"message": "All schemas deleted successfully"}


@app.on_event("startup")
async def startup_event():
    app.state.producer = KafkaProducer(
        {'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})


@app.on_event("shutdown")
async def shutdown_event():
    app.state.producer.close()
