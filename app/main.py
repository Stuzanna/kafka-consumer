import time
import os

from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import SerializationContext, MessageField

from consumer_tools import setup_deserializer

# --- Define Inputs ---
bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:19092')
print(f'KAFKA_BOOTSTRAP_SERVERS: {bootstrap_servers}')
schema_registry_url = os.getenv('SCHEMA_REGISTRY_URL', 'http://localhost:8084')
print(f'SCHEMA_REGISTRY_URL: {schema_registry_url}')
serialization = os.getenv('SERIALIZATION', 'none')
print(f'SERIALIZATION: {serialization}')
schema_loc = os.getenv('SCHEMA_LOC', 'remote')
print(f'SCHEMA_LOC: {schema_loc}')
schema_file_path = os.getenv('SCHEMA_FILE_PATH', None)
topics = os.getenv('TOPICS', 'customers').split(',')
print(f'TOPICS: {topics}')
topics = [topic.strip() for topic in topics] #Strip any extra whitespace
print(f'TOPICS after trim whitespace: {topics}')
sleep_time = int(os.getenv('SLEEP_TIME', '1')) # Sleep between each message
print(f'SLEEP_TIME: {sleep_time}')
client_id = os.getenv('CLIENT_ID', 'my-python-consumer')
print(f'CLIENT_ID: {client_id}')
consumer_group_id = os.getenv('CONSUMER_GROUP_ID', 'my-mostly-pythonic-consumer-group')
print(f'CONSUMER_GROUP_ID: {consumer_group_id}')
auto_offset_reset = os.getenv('AUTO_OFFSET_RESET', 'earliest')
print(f'AUTO_OFFSET_RESET: {auto_offset_reset}')

# -- Consumer Config --
conf = {
    'bootstrap.servers': bootstrap_servers,
    'client.id': client_id,
    'group.id': consumer_group_id,
    # 'security.protocol': 'SSL',
    # 'ssl.ca.location': '../sslcerts/ca.pem',
    # 'ssl.certificate.location': '../sslcerts/service.cert',
    # 'ssl.key.location': '../sslcerts/service.key', 
    'auto.offset.reset': auto_offset_reset,
    }

# SR config, constructor, schema definition, serialization type
schema_registry_conf = {'url': schema_registry_url, 'basic.auth.user.info': '<SR_UserName:SR_Password>'}

schema_registry_client = SchemaRegistryClient(schema_registry_conf)

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