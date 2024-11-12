import json

from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.schema_registry.json_schema import JSONDeserializer

def load_schema(schema_file = None) -> str:
    """
    Load a schema from a local file. Remote schemas can't be loaded from file.

    Parameters:
    ----------
    schema_loc : str
        The location of the schema. Must be either 'local' or 'remote'.
    schema_file : str, optional
        Path to the local schema file (required if `schema_loc` is 'local').

    Returns:
    -------
    str
        The schema as a JSON-formatted string.

    Raises:
    ------
    ValueError
        If schema_loc is not 'local' or if schema_file is missing.
    """
    
    if schema_file is None:
        raise ValueError("Schema file must be provided for local schemas.")
    
    print(f'Loading schema from local file: {schema_file}')
    with open(schema_file, 'r') as file:
        return json.dumps(json.load(file))

def create_deserializer(serialization: str = None, schema_loc: str = None, schema_str: str = None, schema_registry_client = None):
    """
    Create a deserializer based on the specified serialization format.
    If none is specified, no deserializer is created.

    Parameters:
    ----------
    serialization : str
        The serialization format to use. Expected values are 'json' or 'avro'.
    schema_loc : str
        The location of the schema ('local' or 'remote').
    schema_str : str, optional
        The schema in JSON format to use for local schema files.
    schema_registry_client : SchemaRegistryClient, optional
        The client instance for interacting with the Schema Registry.

    Returns:
    -------
    Deserializer
        A deserializer for JSON, Avro or no deserializer if none required.

    Raises:
    ------
    ValueError
        If an invalid parameters provided or required are missing.
    """
    if serialization is None:
        print('No serialization provided, skipping deserializer creation.')
        return None
    elif serialization == 'json':
        if schema_loc == 'remote':
            if schema_registry_client is None:
                raise ValueError("SR client required for remote JSON deserialization.")
            print("Creating JSON deserializer with remote schema...")
            return JSONDeserializer(schema_registry_client=schema_registry_client)
        else:
            if schema_str is None:
                raise ValueError("Schema string required for local JSON deserialization.")
            print("Creating JSON deserializer with local schema...")
            return JSONDeserializer(schema_str)
    
    elif serialization == 'avro':
        if schema_loc == 'remote':
            if schema_registry_client is None:
                raise ValueError("SR client required for remote Avro deserialization.")
            print("Creating Avro deserializer...")
            return AvroDeserializer(schema_registry_client)
        else:
            if schema_str is None:
                raise ValueError("Schema string required for local JSON deserialization.")
            print("Creating Avro deserializer with local schema...")
            return AvroDeserializer(schema_str)
    else:
        raise ValueError(f"Invalid serialization: {serialization}. Expected 'avro', 'json' or None.")

def setup_deserializer(serialization: str = None, schema_loc: str = None, schema_file: str = None, 
                              schema_registry_client = None):
    """
    Set up the appropriate deserializer based on configuration.
    
    Parameters:
    ----------
    serialization : str
        The serialization format to use ('json', 'avro', or None).
    schema_loc : str
        The location of the schema ('local' or 'remote').
    schema_file : str, optional
        Path to the local schema file (required for local schemas).
    schema_registry_client : SchemaRegistryClient, optional
        The client instance for Schema Registry (required only for remote schemas).
        
    Returns:
    -------
    Deserializer
        The configured deserializer instance.
    """
    if serialization is None:
        return create_deserializer()
    
    elif schema_loc == 'local':
        schema_str = load_schema(schema_file)
        return create_deserializer(serialization, schema_loc, schema_str)
    
    elif schema_loc == 'remote':
        return create_deserializer(serialization, schema_loc, 
                                 schema_registry_client=schema_registry_client)
    else:
        raise ValueError(f"Invalid schema location: {schema_loc}. Expected 'local' or 'remote'.")