from confluent_kafka.admin import (AdminClient, NewTopic, 
                                   ConfigResource)
import sys

# return True if topic exists and False if not
def topic_exists(admin, topic):
    metadata = admin.list_topics()
    for t in iter(metadata.topics.values()):
        if t.topic == topic:
            return True
    return False

def create_topic(admin, topic, num_partitions=6, replication_factor=3):
    '''Create new topic and return results dictionary,'''
    new_topic = NewTopic(topic, num_partitions, replication_factor) 
    result_dict = admin.create_topics([new_topic])
    for topic, future in result_dict.items():
        try:
            future.result()  # The result itself is None
            print("Topic {} created".format(topic))
        except Exception as e:
            print(f"Failed to create topic {topic}: {e} Exiting...")
            sys.exit(1) # Causes errors

# get max.message.bytes property
def get_max_size(admin, topic):
    resource = ConfigResource('topic', topic)
    result_dict = admin.describe_configs([resource])
    config_entries = result_dict[resource].result()
    max_size = config_entries['max.message.bytes']
    return max_size.value

# set max.message.bytes for topic
def set_max_size(admin, topic, max_k):
    config_dict = {'max.message.bytes': str(max_k*1024)}
    resource = ConfigResource('topic', topic, config_dict)
    result_dict = admin.alter_configs([resource]) # deprecated
    # result_dict = admin.incremental_alter_configs([resource])
    result_dict[resource].result()

def callback(err, event):
    """
    Delivery report callback for Kafka producer events.

    This function is called once a message is delivered (or failed to be delivered) 
    to a Kafka topic. It handles successful delivery or errors by printing the relevant 
    information about the message and the topic.

    Parameters:
    ----------
    err : KafkaError or None
        The error object, if there was a failure in delivering the message. If `None`, the delivery was successful.
    event : Kafka event object
        The event object representing the message that was sent. Contains details like key, value, topic, and partition.

    Behavior:
    --------
    - If an error occurs (i.e., `err` is not None), it logs the failure message including the topic and event key.
    - If the message is successfully delivered, it logs the key, value (decoded to UTF-8), and the topic partition.
    - Note: Avro-encoded messages may not be fully represented by the decoded value without proper deserialization.
    """

    if err:
        print(f'Produce to topic {event.topic()} failed for event: {event.key()}')
    else:
        key = event.key().decode('utf-8')
        val = event.value().decode('utf8') # won't give full picture for Avro without proper deserializer
        print(f'key:{key} : value:{val} | Sent to \'{event.topic()}\' partition: {event.partition()}.')

import subprocess
import json

def register_schema(schema_registry_url: str, subject_name: str, schema_file_path: str, serialization: str = 'avro'):
    '''
    Register a schema with schema registry.
    Serialization only needed if JSON, assumes AVRO.
    '''
    # Read the schema from the file
    with open(schema_file_path, 'r') as schema_file:
        schema_str = schema_file.read()
    
    if serialization == 'json':
        schema_type = 'JSON'
    else:
        schema_type = 'AVRO'

    payload = {
        "schemaType": schema_type,
        "schema": schema_str

    }

    # Prepare the curl command
    curl_command = [
        "curl",
        "-X", "POST",
        "-H", "Content-Type: application/vnd.schemaregistry.v1+json",
        "-d", json.dumps(payload),
        "-w", "%{http_code}",  # Write the HTTP status code to stdout
        "-s",  # Silent mode (don't show progress meter or error messages)
        "-o", "-",  # Write response body to stdout
        f"{schema_registry_url}/subjects/{subject_name}/versions"
    ]
    
    # Execute the curl command
    result = subprocess.run(curl_command, capture_output=True, text=True)

    # Print the response
    http_status_code = result.stdout[-3:].strip()
    response_body = result.stdout[:-3].strip()

    print("HTTP Status Code:", http_status_code)
    print("Response Code:", result.returncode)
    print("Response Body:", response_body)
    print("Response Error:", result.stderr)

    # # Example usage
    # schema_registry_url = "http://localhost:8084"
    # subject_name = "cars-value2"
    # schema_file_path = "./schemas/cars.avsc"

    # register_schema(schema_registry_url, subject_name, schema_file_path)
