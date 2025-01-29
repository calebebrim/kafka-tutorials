from kafka import KafkaProducer, KafkaConsumer  
import json  

# Producer  
def produce_messages():  
    producer = KafkaProducer(  
        bootstrap_servers='localhost:9092',  
        value_serializer=lambda v: json.dumps(v).encode('utf-8')  
    )  
    topic = 'example_topic'  

    for i in range(5):  
        message = {'id': i, 'value': f'Hello Kafka {i}'}  
        producer.send(topic, message)  
        print(f"Produced: {message}")  

    producer.close()  

# Consumer  
def consume_messages():  
    consumer = KafkaConsumer(  
        'example_topic',  
        bootstrap_servers='localhost:9092',  
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),  
        group_id='example_group',  
        auto_offset_reset='earliest'  
    )  

    print("Consuming messages:")  
    for message in consumer:  
        print(f"Consumed: {message.value}")  

if __name__ == "__main__":  
    produce_messages()  
    consume_messages()  
