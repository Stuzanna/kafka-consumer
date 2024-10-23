import sys
from confluent_kafka.admin import NewTopic

def topic_exists(admin, topic):
    '''return True if topic exists, and False if not.'''
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
