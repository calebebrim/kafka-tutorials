import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from memory_manager import ProtobufMemory
from schemas import ProtobufSchema

# Configure logger
logging.basicConfig(level=logging.INFO)
api_logger = logging.getLogger("api")

app = FastAPI()

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
SCHEMA_TOPIC: str = os.getenv('SCHEMA_TOPIC', 'protobuf_schema_topic')
GROUP_ID: str = os.getenv('GROUP_ID', 'protobuf_schema_registry_group')

# Initialize memory manager for schema storage
schema_memory: ProtobufMemory = ProtobufMemory()

app.state.memory_manager = schema_memory 

class SchemaRequest(BaseModel):
    schema_id: str
    schema_text: str

@app.post("/schemas")
async def create_schema(text: str) -> Dict[str, Any]:
    schema: ProtobufSchema = ProtobufSchema.parse(text)
    if not schema:
        raise HTTPException(status_code=400, detail="Invalid schema format")

    version: int = app.state.memory_manager.add_schema(schema)
    api_logger.info(f"Schema {schema.schema_id} created - Version {version}")
    
    return app.state.memory_manager.get_schema(version).to_json()

@app.get("/schemas/")
async def list_schemas() -> Dict[str, Any]:
    return {"schemas": app.state.memory_manager.list_schemas()}

@app.get("/schemas/{schema_id}")
async def get_schema(schema_id: str) -> Dict[str, Any]:
    schema: ProtobufSchema = app.state.memory_manager.get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"schema_id": schema.schema_id, "version": schema.schema_id_version, "schema": schema.serialize_to_text()}

@app.delete("/schemas/{schema_id}")
async def delete_schema(schema_id: str) -> Dict[str, str]:
    success: bool = app.state.memory_manager.delete_schema(schema_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"message": "Schema deleted"}

@app.delete("/schemas/")
async def delete_all_schemas() -> Dict[str, str]:
    app.state.memory_manager.clear_all()
    return {"message": "All schemas deleted"}

@app.on_event("startup")
async def startup_event() -> None:
    api_logger.info("Starting up...")
    api_logger.info("Startup completed")

@app.on_event("shutdown")
async def shutdown_event() -> None:
    app.state.memory_manager.close()
    api_logger.info("Shutdown completed")
