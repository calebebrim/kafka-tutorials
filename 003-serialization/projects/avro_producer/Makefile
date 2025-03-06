SCHEMA_REGISTRY_URL = http://localhost:8081

register-key-schema:
	curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
		--data '{"schema": "{\"type\": \"string\"}"}' \
		$(SCHEMA_REGISTRY_URL)/subjects/Kafka-key/versions

register-value-schema:
	curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
		--data '{"schema": "{\"type\": \"string\"}"}' \
		$(SCHEMA_REGISTRY_URL)/subjects/Kafka-value/versions

list-subjects:
	curl -X GET $(SCHEMA_REGISTRY_URL)/subjects

list-value-versions:
	curl -X GET $(SCHEMA_REGISTRY_URL)/subjects/Kafka-value/versions

fetch-schema-by-id:
	curl -X GET $(SCHEMA_REGISTRY_URL)/schemas/ids/1

fetch-value-schema-version-1:
	curl -X GET $(SCHEMA_REGISTRY_URL)/subjects/Kafka-value/versions/1

fetch-latest-value-schema:
	curl -X GET $(SCHEMA_REGISTRY_URL)/subjects/Kafka-value/versions/latest

delete-value-schema-version-3:
	curl -X DELETE $(SCHEMA_REGISTRY_URL)/subjects/Kafka-value/versions/3

delete-all-value-schemas:
	curl -X DELETE $(SCHEMA_REGISTRY_URL)/subjects/Kafka-value

check-key-schema-registered:
	curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
		--data '{"schema": "{\"type\": \"string\"}"}' \
		$(SCHEMA_REGISTRY_URL)/subjects/Kafka-key

test-value-schema-compatibility:
	curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
		--data '{"schema": "{\"type\": \"string\"}"}' \
		$(SCHEMA_REGISTRY_URL)/compatibility/subjects/Kafka-value/versions/latest

get-top-level-config:
	curl -X GET $(SCHEMA_REGISTRY_URL)/config

update-global-compatibility:
	curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
		--data '{"compatibility": "NONE"}' \
		$(SCHEMA_REGISTRY_URL)/config

update-value-compatibility:
	curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
		--data '{"compatibility": "BACKWARD"}' \
		$(SCHEMA_REGISTRY_URL)/config/Kafka-value

test-flask-produce:
	curl -X POST -H "Content-Type: application/json" \
		--data '{"name": "test", "value": "Hello, World!"}' \
		http://localhost:9595/test-topic/produce

test-flask-produce-evolution:
	curl -X POST -H "Content-Type: application/json" \
		--data '{"name": "test", "value": "Hello, World!", "version": 2}' \
		http://localhost:9595/test-topic/produce


	curl -X GET $(SCHEMA_REGISTRY_URL)/subjects/test-topic/versions/2
