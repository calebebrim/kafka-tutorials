# project location: src/protobuf/schemas.py
import json
import logging
from google.protobuf import descriptor_pb2, text_format
from typing import Optional, List
import re

# Configure logger
schema_logger = logging.getLogger("protobuf_schemas")

def create_descriptor_from_proto(proto_schema: str, name: str):
    """Parses a Protobuf schema string and creates a FileDescriptorProto dynamically."""
    file_descriptor_proto = descriptor_pb2.FileDescriptorProto()
    file_descriptor_proto.name = f"{name}.proto"
    file_descriptor_proto.syntax = "proto3"

    # Extract message name and fields manually
    lines = proto_schema.splitlines()
    message_name = None
    fields = []
    
    for line in lines:
        line = line.strip()
        if line.startswith("message "):  # Extract message name
            message_name = line.split(" ")[1].strip("{")
        elif "=" in line and ";" in line:  # Extract field definitions
            parts = line.split()
            field_type, field_name, field_number = parts[0], parts[1], int(parts[-1].strip(";").split("=")[-1])
            fields.append((field_type, field_name, field_number))

    if not message_name:
        raise ValueError("Invalid Protobuf schema: No message name found.")

    # Create the message descriptor
    message_descriptor = file_descriptor_proto.message_type.add()
    message_descriptor.name = message_name

    # Define Protobuf type mappings
    type_map = {
        "int32": descriptor_pb2.FieldDescriptorProto.TYPE_INT32,
        "int64": descriptor_pb2.FieldDescriptorProto.TYPE_INT64,
        "float": descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT,
        "double": descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE,
        "bool": descriptor_pb2.FieldDescriptorProto.TYPE_BOOL,
        "string": descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        "bytes": descriptor_pb2.FieldDescriptorProto.TYPE_BYTES,
    }

    # Add fields dynamically
    for field_type, field_name, field_number in fields:
        field_descriptor = message_descriptor.field.add()
        field_descriptor.name = field_name
        field_descriptor.number = field_number
        field_descriptor.type = type_map.get(field_type, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)  # Default to string

    return file_descriptor_proto



class ProtobufSchema:
    __schema_id_version_separator__ = "[svis]"

    def __init__(self, schema_id: str, file_descriptor_proto: descriptor_pb2.FileDescriptorProto, schema_id_version: int = 0):
        """Initialize a Protobuf schema object with metadata exposure."""
        self.schema_id: str = schema_id
        self.schema_proto: descriptor_pb2.FileDescriptorProto = file_descriptor_proto
        self.schema_id_version: int = schema_id_version
        schema_logger.info(f"Creating ProtobufSchema instance for {schema_id} (version {schema_id_version})")

    def compile(self) -> None:
        """Compile the schema dynamically."""
        try:
            if not self.schema_proto.name:
                self.schema_proto.name = f"{self.schema_id}.proto"
            if not self.schema_proto.syntax:
                self.schema_proto.syntax = "proto3"
            schema_logger.info(f"Schema {self.schema_id} compiled successfully.")
        except Exception as e:
            schema_logger.error(f"Failed to compile schema {self.schema_id}: {e}")

    def serialize_to_text(self) -> Optional[str]:
        """Serialize the schema definition to text format."""
        try:
            schema_text = text_format.MessageToString(self.schema_proto)
            return f"{self.schema_id_version}{ProtobufSchema.__schema_id_version_separator__}{schema_text}"
        except Exception as e:
            schema_logger.error(f"Failed to serialize schema {self.schema_id}: {e}")
            return None

    @staticmethod
    def parse(text: str, schema_id:str): 
        """
        Mostly used with a text body like this: '{"schema_id": "test_schema", "schema": "syntax = \"proto3\"; message Test { string name = 1; int32 age = 2; string email = 3; }"}'
        """
        file_descriptor = create_descriptor_from_proto(text, schema_id)

        schema: ProtobufSchema = ProtobufSchema(file_descriptor.name, file_descriptor)
        return schema
    
    def to_json(self):
        return json.dumps(self)

    @staticmethod
    def deserialize_from_text(text: str) -> Optional['ProtobufSchema']:
        """Deserialize a schema definition from text format or raw .proto definition. This is mostly used with serialize_to_text"""
        try:
            schema_id_version = 0
            schema_part = text

            if ProtobufSchema.__schema_id_version_separator__ in text:
                schema_id_version_part, schema_part = text.split(ProtobufSchema.__schema_id_version_separator__, 1)
                try:
                    schema_id_version = int(schema_id_version_part)
                except ValueError:
                    schema_logger.warning(f"Invalid schema_id_version value: {schema_id_version_part}, defaulting to 0")

            file_descriptor_proto = descriptor_pb2.FileDescriptorProto()

            # Check if it's a raw .proto definition
            if "syntax" in schema_part and "message" in schema_part:
                schema_logger.info("Parsing raw .proto schema definition.")
                match = re.search(r'message\s+(\w+)', schema_part)
                if not match:
                    schema_logger.error("Invalid .proto schema: No message type found.")
                    return None
                
                schema_id = match.group(1)
                file_descriptor_proto.name = f"{schema_id}.proto"
                file_descriptor_proto.syntax = "proto3"
                file_descriptor_proto.message_type.add(name=schema_id)
                #This part is odd
            else:
                text_format.Parse(schema_part, file_descriptor_proto)
                schema_id = file_descriptor_proto.name.replace(".proto", "")
            
            schema_logger.info(f"Deserialized schema: {schema_id} (version {schema_id_version})")
            return ProtobufSchema(schema_id, file_descriptor_proto, schema_id_version=schema_id_version)
        except Exception as e:
            schema_logger.error(f"Failed to deserialize schema: {e}")
            return None

    def get_dependencies(self) -> List[str]:
        """Return a list of dependencies for this schema."""
        return list(self.schema_proto.dependency)

    def get_message_types(self) -> List[str]:
        """Return a list of message types defined in this schema."""
        return [msg.name for msg in self.schema_proto.message_type]

    def get_enum_types(self) -> List[str]:
        """Return a list of enum types defined in this schema."""
        return [enum.name for enum in self.schema_proto.enum_type]

    def get_services(self) -> List[str]:
        """Return a list of gRPC service names defined in this schema."""
        return [service.name for service in self.schema_proto.service]

    def get_schema_metadata(self) -> dict:
        """Return metadata about this schema, including its syntax, dependencies, messages, enums, and services."""
        return {
            "schema_id": self.schema_id,
            "schema_id_version": self.schema_id_version,
            "syntax": self.schema_proto.syntax,
            "dependencies": self.get_dependencies(),
            "message_types": self.get_message_types(),
            "enum_types": self.get_enum_types(),
            "services": self.get_services(),
        }
