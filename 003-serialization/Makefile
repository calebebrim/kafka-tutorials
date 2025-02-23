

KIND_VERSION := v0.20.0
KIND_CLUSTER_NAME := my-cluster
DOCKER_REGISTRY := kind-registry
DOCKER_NETWORK := kind


env-up:
	docker-compose up

list-topics:
	docker exec -it kafka kafka-topics --bootstrap-server kafka:9092 --list


test-schema-registry: 
	@curl -X GET http://localhost:8081/subjects
	@echo ""

test-protobuf-server:
	@curl -X GET http://localhost:8080



.PHONY: all install-kind install-tilt install-helm init-docker-repo init-kind-cluster start-kind stop-kind clean

all: install-kind install-tilt install-helm init-docker-repo init-kind-cluster start-kind

install-kind:
	curl -Lo ./kind https://kind.sigs.k8s.io/dl/$(KIND_VERSION)/kind-linux-amd64
	chmod +x ./kind
	sudo mv ./kind /usr/local/bin/kind

install-tilt:
	curl -fsSL https://raw.githubusercontent.com/tilt-dev/tilt/master/scripts/install.sh | bash

install-helm:
	curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

init-docker-repo:
	@if [ -z "$(shell docker ps -q -f name=$(DOCKER_REGISTRY))" ]; then \
		docker run -d --restart=always -p 5000:5000 --name $(DOCKER_REGISTRY) registry:2; \
	fi

init-kind-cluster:
	kind create cluster --name $(KIND_CLUSTER_NAME) --config=kind-config.yaml
	docker network connect $(DOCKER_NETWORK) $(DOCKER_REGISTRY) || true
	echo '127.0.0.1 $(DOCKER_REGISTRY)' | sudo tee -a /etc/hosts

stop-kind:
	kind delete cluster --name $(KIND_CLUSTER_NAME)

clean: stop-kind
	docker stop $(DOCKER_REGISTRY) || true
	docker rm $(DOCKER_REGISTRY) || true
