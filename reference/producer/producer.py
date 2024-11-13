import time
import logging
import sys
import os
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from faker import Faker
from confluent_kafka import Producer, KafkaException
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.admin import AdminClient

from person import Person
from admin_tools import topic_exists, create_topic, register_schema
from producer_tools import load_schema, create_serializer, produce_record

# Producer config
bootstrap_servers = 'localhost:19092'
topic = 'customers-avro' # will autocreate
config = {
    'bootstrap.servers': bootstrap_servers,
    }
sleep_time = 5 # between each message being sent

# SR config, schema definition, serialization type
schema_registry_url = "http://localhost:8084"
schema_registry_conf = {'url': schema_registry_url, 'basic.auth.user.info': '<SR_UserName:SR_Password>'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

schema_loc = 'remote' # local or remote
schema_id = None
subject = 'customers-avro-value'

serialization = "avro" # avro, json, none
schema_file = './schemas/customer-1.avsc' # or .json
cluster_sizing = 'small' # 'small' for demos with 1 broker

# register schema if not already present
register_schema(schema_registry_url, subject, schema_file)

# load schema, from remote schema registry or local file
if serialization in ['json', 'avro']:
    if schema_loc == 'local':
        schema_str = load_schema(schema_loc, schema_file)
    elif schema_loc == 'remote':
        schema_str = load_schema(schema_loc, None, schema_id, subject, schema_registry_url)
    else:
        raise ValueError(f"Invalid schema location: {schema_loc}. Expected 'local' or 'remote'.")
    serializer = create_serializer(serialization, schema_str=schema_str, schema_registry_client=schema_registry_client)
    print(f"Success: Created {serialization.upper()} serializer.")
else:
    create_serializer(serialization, None, None)

# Instantiate Kafka producer and admin client
producer = Producer(config)

admin_client = AdminClient(config)

# Produce the messages
try:
    if not topic_exists(admin_client, topic):
        if cluster_sizing == 'small':
            create_topic(admin_client, topic, num_partitions=3, replication_factor=1)
        else:
            create_topic(admin_client, topic)
except Exception as e:
        print(f"Failed to create topic {topic}: {e}. Exiting...")

try:
    print("Start producing messages.")
    while True:
        try:
            if topic == 'cars':
                message = {
                    "make": "BMW-python",
                    "model": "70-series",
                    "year": "2024",
                    "color": "red"
                }
                key = "car-manual"
            else:
                fake = Faker()
                person = Person(fake.name(), fake.address(), fake.email())
                message = {
                    "name": person.name,
                    "address": person.address,
                    "email": person.email,
                    "timestamp": person.timestamp,
                }
                key = person.extract_state()

            payload = {
                "key": key,
                "message": message
            }
            produce_record(producer, payload['message'], payload['key'], topic, serialization, serializer)
            producer.flush()
            time.sleep(sleep_time)
        except KafkaException as e:
            logging.error(f"Produce message error: {e}")
            break
except KeyboardInterrupt:
    print("KeyboardInterrupt. Stopping the producer...")
finally:
    print("Attempting to flush the producer...")
    producer.flush()
    print("Producer has been flushed.")
