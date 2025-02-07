#!/bin/bash

# REST API endpoint
API_URL="http://localhost:5000/bronze/produce"

# JSON message payload with realistic data
MESSAGE='{
  "user_id": 12345,
  "timestamp": "2025-02-05T12:34:56Z",
  "event_type": "purchase",
  "amount": 49.99,
  "currency": "USD",
  "items": [
    {"item_id": "A100", "quantity": 2, "price": 19.99},
    {"item_id": "B200", "quantity": 1, "price": 9.99}
  ]
}'

# Send POST request to the REST API
curl -X POST "$API_URL" \
     -H "Content-Type: application/json" \
     -d "$MESSAGE"

# Print response
echo "\nRealistic message sent to Kafka via REST API."
