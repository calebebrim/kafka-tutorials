SHELL := /bin/bash

# Variables
PYTHON := python3
VENV := .venv
ACTIVATE := source $(VENV)/bin/activate

# Create virtual environment and install dependencies
setup:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install -r requirements.txt

# Run the FastAPI server
deploy:
	$(ACTIVATE) && uvicorn protobuf_schema_registry:app --host 0.0.0.0 --port 8000

# Test adding multiple versions of a schema
test-create-multiple:
	curl -X POST "http://localhost:8000/schemas" \
	-H "Content-Type: text/plain" \
	-d <<EOF \
		syntax = "proto3"; \ 
		message Test { \
			string name = 1; \ 
		} \
	EOF
	@echo ''
	@echo '----'
	curl -X POST "http://localhost:8000/schemas" \
	-H "Content-Type: text/plain" \
	-d 'syntax = "proto3"; message Test { string name = 1; int32 age = 2; }'
	@echo ''
	@echo '----'
	curl -X POST "http://localhost:8000/schemas" \
	-H "Content-Type: text/plain" \
	-d 'syntax = "proto3"; message Test { string name = 1; int32 age = 2; string email = 3; }'
	@echo ''
	@echo '----'

# Test retrieving the latest schema version
test-get-latest:
	curl -X GET "http://localhost:8000/schemas/test_schema"

# Test retrieving all versions of the schema
test-get-all:
	for i in {1..3}; do \
		curl -X GET "http://localhost:8000/schemas/test_schema?version=$$i"; \
		echo "\n"; \
	done

# Test retrieving a non-existing schema
test-get-notfound:
	curl -X GET "http://localhost:8000/schemas/non_existing_schema"

# Cleanup virtual environment
clean:
	rm -rf $(VENV)

# Cleanup all schemas from the server
test-delete-all:
	curl -X DELETE "http://localhost:8000/schemas/"



