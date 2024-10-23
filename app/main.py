import time
import os

from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import SerializationContext, MessageField

from consumer_tools import setup_deserializer

# --- Define Inputs ---
bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:19092')
print(f"Using bootstrap servers: {bootstrap_servers}")

schema_registry_url = os.getenv('SCHEMA_REGISTRY_URL', 'http://localhost:8084')
print(f"Using schema registry url: {schema_registry_url}")

serialization = os.getenv('SERIALIZATION', 'none')
print(f"Using serialization: {serialization}")

schema_loc = os.getenv('SCHEMA_LOC', 'remote')
print(f"Using schema location: {schema_loc}")

topic_names = os.getenv('TOPICS', "customers").split(',')
print(f"Using topics: {topic_names}")
topic_names = [topic.strip() for topic in topic_names] #Strip any extra whitespace
print(f"Topic values after whitespace: {topic_names}")

# -- Consumer Config --
topics = topic_names
sleep_time = 1 # Sleep between each message
client_id = "my-python-consumer"
consumer_group_id = "my-pythonic-consumer-group"
offset_config = "earliest"
conf = {
    'bootstrap.servers': bootstrap_servers,
    'client.id': client_id,
    'group.id': consumer_group_id,
    # 'security.protocol': 'SSL',
    # 'ssl.ca.location': '../sslcerts/ca.pem',
    # 'ssl.certificate.location': '../sslcerts/service.cert',
    # 'ssl.key.location': '../sslcerts/service.key', 
    'auto.offset.reset': offset_config,
    }

# SR config, constructor, schema definition, serialization type
schema_registry_conf = {'url': schema_registry_url, 'basic.auth.user.info': '<SR_UserName:SR_Password>'}

schema_registry_client = SchemaRegistryClient(schema_registry_conf)

serialization = "none"
schema_loc = 'remote' # local or remote
# schema_file = './schemas/customer-1.avsc' # or .json

# --- Set the deserializer ---
deserializer = setup_deserializer(serialization, schema_loc, schema_registry_client=schema_registry_client)

# --- Creating the Consumer ---
consumer = Consumer(conf)

# --- Running the consumer ---
try:
    consumer.subscribe(topics)
    print(f"Subscribed to topics: {topics}")

    while True:
        try:
            msg = consumer.poll(timeout = 3.5)
            if msg is None: 
                print("Waiting for message...")
                continue

            else:
                    key = msg.key().decode('utf-8')
                    if serialization in ['json', 'avro']:
                          value = deserializer(msg.value(), SerializationContext(topics[0], MessageField.VALUE))
                    elif serialization == 'none':
                        value = msg.value().decode('utf-8')
                    else:
                        raise ValueError(f"Invalid serialization type: {serialization}. Expected 'avro', 'json' or 'none'.")
                    
                    print(f"{msg.partition()}:{msg.offset()}: "
                        f"k={key} "
                        f"v={value}")
                    time.sleep(sleep_time)  

        except KeyboardInterrupt:
            print("KeyboardInterrupt detected. Stopping the consumer...")
            break
        except Exception as e:
            print(f"Error reading message at {msg.partition()}:{msg.offset()}. Error =  {e}")
finally:
    # Close down consumer to commit final offsets.
    print("Attempting to close the consumer...")
    consumer.close()
    print("Consumer closed.")    