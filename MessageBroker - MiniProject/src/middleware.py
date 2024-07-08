"""Middleware to communicate with PubSub Message Broker."""
from collections.abc import Callable
from enum import Enum
from queue import LifoQueue, Empty
from typing import Any
import socket
import json
import pickle
import xml.etree.ElementTree as xml


class MiddlewareType(Enum):
    """Middleware Type."""

    CONSUMER = 1
    PRODUCER = 2


class Queue:
    """Representation of Queue interface for both Consumers and Producers."""

    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        """Create Queue."""
        self.topic = topic
        self._type = _type
        
        # Initialize socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.connect(("localhost", 5000))
    
    def encode(self, data: Any):
        """Encodes data to be sent."""
        pass

    def decode(self, data: Any):
        """Decodes data to be sent."""
        pass

    def format(self, action, topic=None, value=None):
        """Formats data to be sent."""
        pass

    def push(self, value):
        """Sends data to broker."""
        message = self.encode(self.format("publish", topic=self.topic, value=value))
        self.send(message)

    def pull(self) -> tuple[str, Any]:
        """Receives (topic, data) from broker.

        Should BLOCK the consumer!"""

        header = self.sock.recv(2)
        size = int.from_bytes(header, "big")
        message = self.sock.recv(size)
        
        if len(message) != 0:
            data = self.decode(message)
            if "topic" not in data.keys():
                topic = None
            else:
                topic = data["topic"]

            if "value" not in data.keys():
                value = None
            else:    
                value = data["value"]

            return topic, value

    def list_topics(self, callback: Callable):
        """Lists all topics available in the broker."""
        message = self.encode(self.format("list_topics"))
        self.send(message)

    def cancel(self):
        """Cancel subscription."""
        message = self.encode(self.format("cancel", topic=self.topic))
        self.send(message)
        
    
    def send(self,message):
        message =  len(message).to_bytes(2, "big") + message
        self.sock.send(message)

class JSONQueue(Queue):
    """Queue implementation with JSON based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic, _type)
        message = self.encode(self.format("format", value="json"))
        self.send(message)

        if self._type == MiddlewareType.CONSUMER:
            message = self.encode(self.format("subscribe", topic=str(self.topic)))
            self.send(message)
    
    def encode(self, data: Any):
        return (json.dumps(data)).encode("utf-8")
    
    def decode(self, data: Any):
        return json.loads(data.decode("utf-8"))

    def format(self, action, topic=None, value=None):
        message = {"action": action}
        if topic != None:
            message["topic"] = topic
        if value != None:
            message["value"] = value
        return message


class XMLQueue(Queue):
    """Queue implementation with XML based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic, _type)
        message = self.encode(self.format("format", value="xml"))
        self.send(message)

        if self._type == MiddlewareType.CONSUMER:
            message = self.encode(self.format("subscribe", topic=str(self.topic)))
            self.send(message)
    
    def encode(self, data: Any):
        return data.encode("utf-8")
    
    def decode(self, data: Any):
        tree = xml.ElementTree(xml.fromstring(data.decode("utf-8")))           
        data = {}
        
        for el in tree.iter():
            data[el.tag] = el.text

        return data

    def format(self, action, topic=None, value=None):
        if topic == None and value == None:
            return f"<data><action>{action}</action></data>"
        elif value == None:
            return f"<data><action>{action}</action><topic>{topic}</topic></data>"
        elif topic == None:
            return f"<data><action>{action}</action><value>{value}</value></data>"
        else:
            return f"<data><action>{action}</action><topic>{topic}</topic><value>{value}</value></data>"


class PickleQueue(Queue):
    """Queue implementation with Pickle based serialization."""
    def __init__(self, topic, _type=MiddlewareType.CONSUMER):
        super().__init__(topic, _type)
        message = self.encode(self.format("format", value="pickle"))
        self.send(message)

        if self._type == MiddlewareType.CONSUMER:
            message = self.encode(self.format("subscribe", topic=str(self.topic)))
            self.send(message)
    
    def encode(self, data: Any):
        return pickle.dumps(data)
    
    def decode(self, data: Any):
        return pickle.loads(data)
    
    def format(self, action, topic=None, value=None):
        message = {"action": action}
        if topic != None:
            message["topic"] = topic
        if value != None:
            message["value"] = value
        return message
