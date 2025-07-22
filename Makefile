.PHONY: build test run stop clean validate logs shell push

# Variables
IMAGE_NAME = mt5-docker-api
CONTAINER_NAME = mt5-test
DOCKER_REPO = jefrnc/mt5-docker-api

# Build the Docker image
build:
	@echo "Building Docker image..."
	docker build -t $(IMAGE_NAME):latest .

# Run tests
test: build
	@echo "Starting test container..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for services to start..."
	sleep 30
	@echo "Running validation..."
	python3 scripts/validate.py || true
	@echo "Stopping test container..."
	docker-compose -f docker-compose.test.yml down

# Run the container
run:
	@echo "Starting container..."
	docker-compose up -d

# Stop the container
stop:
	@echo "Stopping container..."
	docker-compose down

# Clean up
clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker rmi $(IMAGE_NAME):latest || true
	rm -rf test-config/

# Validate running container
validate:
	@echo "Validating running container..."
	python3 scripts/validate.py

# View logs
logs:
	docker-compose logs -f

# Shell into container
shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

# Push to Docker Hub
push: build
	@echo "Tagging image..."
	docker tag $(IMAGE_NAME):latest $(DOCKER_REPO):latest
	@echo "Pushing to Docker Hub..."
	docker push $(DOCKER_REPO):latest

# Quick test build
quick-test:
	@echo "Quick build test..."
	docker build --target base -t $(IMAGE_NAME):test .

# Full test suite
full-test: clean build test validate
	@echo "Full test completed!"