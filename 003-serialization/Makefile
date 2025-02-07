

env-up:
	docker-compose up

list-topics:
	docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --list


test-schema-registry: 
	@curl -X GET http://localhost:8081/subjects
	@echo ""

test-protobuf-server:
	@curl -X GET http://localhost:8080


