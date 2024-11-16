import re

from datetime import datetime

class Person(object):
    def __init__(self, name, address, email):
        self.name = name
        self.address = address
        self.email = email
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        return f"{self.name}, lives at {self.address}, contactable at {self.email}, generated at {self.timestamp}"
    
    def extract_state(self):
        # Regular expression to capture the state abbreviation
        match = re.search(r'\b([A-Z]{2})\b', self.address)
        if match:
            return match.group(1)
        return None

def person_timestamp_str_to_num(person: Person) -> Person:
            dt = datetime.strptime(person.timestamp, "%Y-%m-%d %H:%M:%S")
            person.timestamp = int(dt.timestamp())
