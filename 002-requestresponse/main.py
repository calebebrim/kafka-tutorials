import argparse
import json
import threading
import uuid
import time
import logging
from flask import Flask, request, jsonify
from confluent_kafka import Producer, Consumer, KafkaError
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import signal
import sys





logger = None

# Set up logging
def setup_logging(log_level):
    global logger
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

# Kafka and Prometheus constants
KAFKA_BROKER = 'localhost:9092'
REQUEST_TOPIC = 'requests'
RESPONSE_TOPIC = 'responses'

# Kafka Producer Configuration
producer_conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'acks': 'all',
    'enable.idempotence': True
}
producer = Producer(producer_conf)

# Kafka Consumer Configuration
rest_consumer_conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': 'response_handler',
    'auto.offset.reset': 'latest'
}

# Kafka Consumer Configuration for backend processor
backend_processor_conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': 'backend_processor',
    'auto.offset.reset': 'latest'
}

app = Flask(__name__)
requests_events = {}
responses = {}

# Global metrics store
previous_requests_received = 0
previous_requests_timeouts = 0
previous_kafka_responses_received = 0
previous_kafka_requests_processed = 0
last_update_time = time.time()

# Event to signal interruption
shutdown_event = threading.Event()

# Request Metrics
REQUESTS_RECEIVED = None
REQUEST_TIMEOUTS = None
REQUEST_RESPONSE_TIME = None
REQUEST_RESPONSES_RECEIVED = None
REQUEST_RECEIVED_RATE = None
REQUEST_TIMEOUTS_RATE = None
REQUEST_RESPONSES_RECEIVED_RATE = None

# Backend Metrics
BACKEND_REQUESTS_PROCESSED = None
BACKEND_REQUESTS_PROCESSED_RATE = None

def setup_request_metrics():
    global REQUESTS_RECEIVED, REQUEST_TIMEOUTS, REQUEST_RESPONSE_TIME, REQUEST_RESPONSES_RECEIVED, REQUEST_RECEIVED_RATE, REQUEST_TIMEOUTS_RATE, REQUEST_RESPONSES_RECEIVED_RATE
    REQUESTS_RECEIVED = Counter('requests_received', 'Total number of requests received')
    REQUEST_TIMEOUTS = Counter('requests_timeouts', 'Total number of requests that timed out')
    REQUEST_RESPONSE_TIME = Histogram('requests_response_time_seconds', 'Histogram of request response times (in seconds)')
    REQUEST_RESPONSES_RECEIVED = Counter('kafka_responses_received', 'Total number of Kafka responses received')
    REQUEST_RECEIVED_RATE = Gauge('requests_received_rate', 'Rate of requests received per second')
    REQUEST_TIMEOUTS_RATE = Gauge('requests_timeouts_rate', 'Rate of requests that timed out per second')
    REQUEST_RESPONSES_RECEIVED_RATE = Gauge('kafka_responses_received_rate', 'Rate of Kafka responses received per second')

def setup_backend_metrics():
    global BACKEND_REQUESTS_PROCESSED, BACKEND_REQUESTS_PROCESSED_RATE
    BACKEND_REQUESTS_PROCESSED = Counter('kafka_requests_processed', 'Total number of Kafka requests processed')
    BACKEND_REQUESTS_PROCESSED_RATE = Gauge('kafka_requests_processed_rate', 'Rate of Kafka requests processed per second')

def delivery_report(err, msg, threadId=None):
    """Kafka delivery callback."""
    prefix = f"[{threadId}] " if threadId else ""
    if err is not None:
        logger.error(f'{prefix}Error delivering message to "{msg.partition()}@{msg.topic()}": {err}')
    else:
        logger.info(f'{prefix}Message delivered to "{msg.partition()}@{msg.topic()}"')



def consume_backend_responses():
    """Thread that listens for responses from Kafka and signals waiting requests."""
    global previous_kafka_responses_received
    global last_update_time
    consumer = Consumer(rest_consumer_conf)
    consumer.subscribe([RESPONSE_TOPIC])
    logger.info(f"consume_backend_responses subscribed to {RESPONSE_TOPIC}")
    while not shutdown_event.is_set():
        logger.debug(f"Waiting for Kafka message at {RESPONSE_TOPIC}...")
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            logger.debug("No message received in this poll iteration.")
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                logger.debug(f"End of partition reached: {msg.partition()}")
                continue
            else:
                logger.error(f'Consumer error: {msg.error()}')
                continue
        
        logger.debug(f"Received message from Kafka: {msg.value().decode('utf-8')}")
        response = json.loads(msg.value().decode('utf-8'))
        req_id = response.get('request_id')
        if req_id and req_id in requests_events:
            responses[req_id] = response
            requests_events[req_id].set()  # Notify waiting thread
            REQUEST_RESPONSES_RECEIVED.inc()  # Increment Kafka response counter
            logger.debug(f"Response for request ID {req_id} received and event set.")
        
        # Calculate the rate change for Kafka responses received
        current_time = time.time()
        if current_time - last_update_time > 1:
            rate = REQUEST_RESPONSES_RECEIVED._value.get() - previous_kafka_responses_received
            REQUEST_RESPONSES_RECEIVED_RATE.set(rate)
            previous_kafka_responses_received = REQUEST_RESPONSES_RECEIVED._value.get()
            last_update_time = current_time
            logger.debug(f"Kafka responses rate updated: {rate} responses per second")

@app.route('/request', methods=['POST'])
def handle_request():
    """Handles incoming HTTP requests and routes them through Kafka."""
    global previous_requests_received, previous_requests_timeouts
    req_id = str(uuid.uuid4())
    headers = dict(request.headers)
    payload = request.json
    message = {
        'request_id': req_id,
        'headers': headers,
        'payload': payload
    }
    
    requests_events[req_id] = threading.Event()
    start_time = time.time()
    
    logger.debug(f"Handling request: {req_id}")
    REQUESTS_RECEIVED.inc()  # Increment counter for received requests

    # Log the incoming request
    logger.info(f'Received request with ID: {req_id}')

    # Calculate the rate change for requests received
    current_time = time.time()
    if current_time - last_update_time > 1:
        rate = REQUESTS_RECEIVED._value.get() - previous_requests_received
        REQUEST_RECEIVED_RATE.set(rate)
        previous_requests_received = REQUESTS_RECEIVED._value.get()
        logger.debug(f"Requests rate updated: {rate} requests per second")

    logger.debug(f"Producing message to Kafka: {message}")
    producer.produce(REQUEST_TOPIC, key=req_id, value=json.dumps(message), callback=delivery_report)
    producer.flush()
    
    # Wait for response (timeout after 10 seconds)
    logger.debug(f"Waiting for response to request ID: {req_id}")
    if requests_events[req_id].wait(timeout=10):
        response = responses.pop(req_id, {'error': 'No response received'})
        end_time = time.time()
        REQUEST_RESPONSE_TIME.observe(end_time - start_time)  # Record response time
        del requests_events[req_id]
        logger.info(f'Response received for request ID: {req_id}')
        return jsonify(response)
    else:
        REQUEST_TIMEOUTS.inc()  # Increment timeout counter
        # Calculate the rate change for request timeouts
        rate = REQUEST_TIMEOUTS._value.get() - previous_requests_timeouts
        REQUEST_TIMEOUTS_RATE.set(rate)
        previous_requests_timeouts = REQUEST_TIMEOUTS._value.get()
        
        del requests_events[req_id]
        logger.warning(f'Request ID {req_id} timed out')
        return jsonify({'error': 'Request timed out'}), 504

def backend_processor(threadId):
    """Backend service that reads requests and produces responses."""
    global previous_kafka_requests_processed
    consumer = Consumer(backend_processor_conf)
    consumer.subscribe([REQUEST_TOPIC])
    logger.info(f"[{threadId}]backend_processor subscribed to {REQUEST_TOPIC} topic.")
    
    while not shutdown_event.is_set():
        logger.debug(f"[{threadId}]Waiting for request in backend processor at {REQUEST_TOPIC} topic...")
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f'[{threadId}]Consumer error: {msg.error()}')
            continue
        
        logger.debug(f"[{threadId}]Backend processor received request: {msg.value().decode('utf-8')}")
        request_data = json.loads(msg.value().decode('utf-8'))
        response_data = {
            'request_id': request_data['request_id'],
            'headers': request_data['headers'],
            'payload': request_data['payload'],
            'response': 'Processed successfully'
        }
        
        logger.debug(f"[{threadId}]Producing response to Kafka: {response_data}")
        producer.produce(RESPONSE_TOPIC, key=request_data['request_id'], value=json.dumps(response_data), callback=lambda *args: delivery_report(*args, threadId))
        producer.flush()
        BACKEND_REQUESTS_PROCESSED.inc()  # Increment Kafka requests processed counter

        # Calculate the rate change for Kafka requests processed
        rate = BACKEND_REQUESTS_PROCESSED._value.get() - previous_kafka_requests_processed
        BACKEND_REQUESTS_PROCESSED_RATE.set(rate)
        previous_kafka_requests_processed = BACKEND_REQUESTS_PROCESSED._value.get()

@app.route('/metrics')
def metrics():
    """Expose Prometheus metrics."""
    from prometheus_client import generate_latest
    return generate_latest()




def main():
    parser = argparse.ArgumentParser(description="Backend service options")
    parser.add_argument('--no-http', action='store_true', help="Disable HTTP server")
    parser.add_argument('--num-backend-threads', type=int, default=1, help="Number of backend threads")
    parser.add_argument('--no-backend', action='store_true', help="Disable backend processor")
    parser.add_argument('--no-metrics', action='store_true', help="Disable metrics server")
    parser.add_argument('--metrics-port', type=int, default=8000, help="Set the metrics server port")
    parser.add_argument('--log-level', '-l', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Set the log level")
    
    args = parser.parse_args()

    # Set logging level based on the argument
    setup_logging(args.log_level)

    # Start the Prometheus metrics server if not disabled
    if not args.no_metrics:
        logger.debug(f"Starting Prometheus metrics server on port {args.metrics_port}")
        start_http_server(args.metrics_port)

    # Initialize request metrics only if no-http is False
    app_thread = None
    consume_backend_resp_thread = None
    if not args.no_http:
        setup_request_metrics()
        # Start HTTP server thread
        app_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
        app_thread.daemon = True
        app_thread.start()

        # Start response consumer thread
        consume_backend_resp_thread = threading.Thread(target=consume_backend_responses)
        consume_backend_resp_thread.daemon = True
        consume_backend_resp_thread.start()

    # Initialize backend metrics only if no-backend is False
    if not args.no_backend:
        setup_backend_metrics()
        backend_threads = []
        for threadId in range(args.num_backend_threads):
            thread = threading.Thread(target=backend_processor, args=(threadId,), daemon=True)
            backend_threads.append(thread)
            thread.start()

    

    # Log server startup
    logger.info("Service started.")

    # Wait for all threads to finish (by joining)
    try:
        if app_thread:
            app_thread.join()
        if consume_backend_resp_thread: 
            consume_backend_resp_thread.join()
        for thread in backend_threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        shutdown_event.set()

def handle_signal(signum, frame):
    """Signal handler function."""
    print(f"Received signal {signum}, shutting down gracefully.")
    shutdown_event.set()
    sys.exit(0)  # Exit gracefully

# Catch SIGINT (Ctrl+C) and SIGTERM (Termination signal)
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

if __name__ == '__main__':

    main()
