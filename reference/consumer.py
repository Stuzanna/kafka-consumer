import time

from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import SerializationContext, MessageField

from consumer_tools import load_schema, create_deserializer

# -- Consumer Config --
bootstrap_servers = "localhost:19092"
topics = ["customers"]
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
schema_registry_url = "http://localhost:8081"
schema_registry_conf = {'url': schema_registry_url, 'basic.auth.user.info': '<SR_UserName:SR_Password>'}

schema_registry_client = SchemaRegistryClient(schema_registry_conf)

schema_loc = 'local' # local or remote
schema_file = './schemas/customer-1.avsc' # or .json
schema_id = 1
subject = 'customers-value'

serialization = "none"

# --- Create deserializer ---
if serialization in ['json', 'avro']:
    if schema_loc == 'local':
        schema_str = load_schema(schema_loc, schema_file)
    elif schema_loc == 'remote':
        schema_str = load_schema(schema_loc, None, schema_id, schema_registry_url)
    else:
        raise ValueError(f"Invalid schema location: {schema_loc}. Expected 'local' or 'remote'.")
    
    deserializer = create_deserializer(serialization, schema_str, schema_registry_client)
    print(f"Success: Created {serialization.upper()} serializer.")
else:
    create_deserializer(serialization, None, None)

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