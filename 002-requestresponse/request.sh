#!/bin/bash

# Test HTTP request script
API_URL="http://localhost:5000/request"

echo "Sending test request to $API_URL..."

response=$(curl -s -X POST "$API_URL" \
     -H "Content-Type: application/json" \
     -H "Custom-Header: TestValue" \
     -d '{"message": "Hello Kafka!"}')

echo "\nResponse received: $response"
