import json
import requests

from confluent_kafka.schema_registry.json_schema import JSONSerializer
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField

# Callback fn
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

# Create serializer based on schema location and serialization format
def load_schema(schema_loc: str, schema_file = None, schema_id = None, subject = None, schema_registry_url = None) -> str:
    """
    Load a schema based on the provided schema location (local or remote).
    This could be rewritten to make better use of the schema_registry_client for registering and working with schemas, not the HTTP calls directly done here.

    This function loads a schema either from a local file or by fetching it 
    from a remote schema registry, depending on the specified `schema_loc`.

    Parameters:
    ----------
    schema_loc : str
        The location of the schema. Must be either 'local' or 'remote'.
    schema_file : str, optional
        Path to the local schema file (required if `schema_loc` is 'local').
    schema_id : int, optional
        The ID of the schema to fetch from the schema registry an alternative to subject (required if `schema_loc` is 'remote').
    subject: str, optional
        The schema subject name to fetch  the schema registry, an alternative to schema_id (required if `schema_loc` is 'remote').
    schema_registry_url : str, optional
        The base URL of the schema registry (required if `schema_loc` is 'remote').

    Returns:
    -------
    str
        The schema as a JSON-formatted string.

    Raises:
    ------
    ValueError
        If required arguments are missing or an invalid schema location is provided.
    """
    if schema_loc == 'local':
        if schema_file is None:
            raise ValueError("Schema file must be provided for local schemas.")
        print(f'Loading schema from local file: {schema_file}')
        with open(schema_file, 'r') as f:
            return json.dumps(json.load(f))
    elif schema_loc == 'remote':
        if schema_registry_url is None:
            raise ValueError("Schema registry URL must be provided for remote schemas.")
        if schema_id is not None:
            print(f"Fetching schema from remote: {schema_registry_url}")
            response = requests.get(f"{schema_registry_url}/schemas/ids/{schema_id}")
            return response.json()["schema"]
        if subject is not None:
            print(f"Fetching latest schema for subject: {subject}")
            response = requests.get(f"{schema_registry_url}/subjects/{subject}/versions/latest")
            print(f"response: {response}")
            return response.json()["schema"]
                    
        raise ValueError("Either schema_id or subject must be provided for remote schema")

    else:
        raise ValueError(f"Invalid schema location: {schema_loc}. Expected 'local' or 'remote'.")
    
def create_serializer(serialization, schema_str = None, schema_registry_client = None):
    """
    Create a serializer based on the specified serialization format.

    Depending on the `serialization` parameter, this function creates and returns a 
    JSON or Avro serializer using the provided schema string and Schema Registry client.
    If 'none' is specified, no serializer is created.
    Note, Avro always requires a schema registry client due to limits in the library.

    Parameters:
    ----------
    serialization : str
        The serialization format to use. Expected values are 'json', 'avro', or 'none'.
    schema_str : str
        The schema in JSON format to use for serialization.
    schema_registry_client : SchemaRegistryClient
        The client instance for interacting with the Schema Registry.
    
    Returns:
    -------
    JSONSerializer, AvroSerializer, or None
        A serializer for JSON or Avro based on the `serialization` type, or None if no serialization is selected.

    Raises:
    ------
    ValueError
        If an invalid serialization type is provided.
    """
    if serialization == 'json':
        print("Creating JSON serializer...")
        return JSONSerializer(schema_str, schema_registry_client) if schema_registry_client is not None else JSONSerializer(schema_str, conf={"auto.register.schemas":False})
    elif serialization == 'avro':
        print("Creating Avro serializer...")
        return AvroSerializer(schema_registry_client, schema_str) if schema_registry_client is not None else AvroSerializer(schema_str=schema_str, conf={"auto.register.schemas":False})
    elif serialization == 'none':
        print('No serialization selected, skipping serializer creation.')
        return None
    else:
        raise ValueError(f"Invalid serialization: {serialization}. Expected 'avro', 'json' or 'none'.")

def produce_record(producer, payload, key, topic, serialization, serializer):
    """
    Produce a record to a Kafka topic with the specified serialization.

    This function serializes the given `payload` based on the `serialization` type
    and sends it to the specified Kafka `topic` using the provided `producer`.
    It handles 'json' and 'avro' serialization formats, or sends the payload as JSON
    without schema if 'none' is specified.

    Parameters:
    ----------
    producer : KafkaProducer
        The Kafka producer instance used to send the message.
    payload : dict
        The data to be serialized and sent to the Kafka topic.
    key : str
        The key associated with the message.
    topic : str
        The Kafka topic to which the message is sent.
    serialization : str
        The serialization format to use. Expected values are 'json', 'avro', or 'none'.

    Raises:
    ------
    ValueError
        If an invalid serialization type is provided.

    Notes:
    -----
    - For 'json' and 'avro' serialization, the function uses the `serializer` function
      with the provided `SerializationContext`.
    - When `serialization` is 'none', the payload is encoded as JSON without schema validation.
    - The `producer.poll(1)` call ensures that the message is processed before the function exits.
    """
    if serialization in ['json', 'avro']:
        value = serializer(payload, SerializationContext(topic, MessageField.VALUE))
    elif serialization == 'none':
        value = json.dumps(payload).encode('utf-8') # no schema, just send json
    else:
        raise ValueError(f"""
                         Invalid serializer: {serialization}. Expected 'avro', 'json' or 'none'.
                         """)
    producer.produce(topic, value, key, on_delivery=callback)
    producer.poll(1)
