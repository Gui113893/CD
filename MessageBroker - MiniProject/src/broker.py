"""Message Broker"""
import enum
import socket
from typing import Dict, List, Any, Tuple
import selectors
import json
import pickle
import xml.etree.ElementTree as xml


class Serializer(enum.Enum):
    """Possible message serializers."""

    JSON = 0
    XML = 1
    PICKLE = 2

    def getSerializer(value):
        if value == "json":
            return Serializer.JSON
        elif value == "xml":
            return Serializer.XML
        elif value == "pickle":
            return Serializer.PICKLE  

class Broker:
    """Implementation of a PubSub Message Broker."""

    def __init__(self):
        """Initialize broker."""
        self.canceled = False
        self._host = "localhost"
        self._port = 5000

        # Initialize socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self._host, self._port))
        self.socket.listen(100)

        # Initialize selector
        self.selelector = selectors.DefaultSelector()
        self.selelector.register(self.socket, selectors.EVENT_READ, self.accept) 

        # Initialize topics dictionary
        self.topics={} # {topic: [[(socket,Serializer),...], value]}
        self.sockets={} # {socket: Serializer}
 
    def list_topics(self) -> List[str]:
        """Returns a list of strings containing all topics containing values."""
        topic_list = []
        for k, v in self.topics.items():
            if v[1] != None:
                topic_list.append(k)
        return topic_list
            
    
    def get_topic(self, topic):
        """Returns the currently stored value in topic."""
        for k, v in self.topics.items():
            if topic == k:
                if v[1] != None:
                    return v[1]
        return None
    
    def put_topic(self, topic, value):
        """Store in topic the value."""
        keys = self.topics.keys()
        if topic in keys:
            self.topics[topic][1] = value
        else:
            self.topics[topic] = [[],value]

    def list_subscriptions(self, topic: str) -> List[Tuple[socket.socket, Serializer]]:
        """Provide list of subscribers to a given topic."""
        return self.topics.get(topic)[0]
    
    def subscribe(self, topic: str, address: socket.socket, _format: Serializer = None):
        """Subscribe to topic by client in address."""
        if topic in self.topics.keys():
            if (address,_format) not in self.topics[topic][0]:
                self.topics[topic][0].append((address,_format))
        else:
            self.topics[topic] = [[(address,_format)],None]

    def unsubscribe(self, topic, address):
        """Unsubscribe to topic by client in address."""
        for i in self.topics[topic][0]:
            if(i[0]==address):
                self.topics[topic][0].remove(i)
                break
    
    def format(self, action, topic=None, value=None, serialization=None):
        """Format message."""
        if serialization == Serializer.JSON or serialization == Serializer.PICKLE:
            message = {"action": action}
            if topic != None:
                message["topic"] = topic
            if value != None:
                message["value"] = value
            return message
        elif serialization == Serializer.XML:
            if topic == None and value == None:
                return f"<data><action>{action}</action></data>"
            elif value == None:
                return f"<data><action>{action}</action><topic>{topic}</topic></data>"
            elif topic == None:
                return f"<data><action>{action}</action><value>{value}</value></data>"
            else:
                return f"<data><action>{action}</action><topic>{topic}</topic><value>{value}</value></data>"
    
    def encode(self, message, serialization):
        """Encode message."""
        if serialization == Serializer.JSON:
            return (json.dumps(message)).encode("utf-8")
        elif serialization == Serializer.XML:
            return message.encode("utf-8")
        elif serialization == Serializer.PICKLE:
            return pickle.dumps(message)
            
    def decode(self, message, serialization):
        """Decode message."""
        if serialization == Serializer.JSON:
            return json.loads(message.decode("utf-8"))
        elif serialization == Serializer.XML:
            tree = xml.ElementTree(xml.fromstring(message.decode("utf-8")))           
            message = {}

            for el in tree.iter():
                message[el.tag] = el.text

            return message
        elif serialization == Serializer.PICKLE:
            return pickle.loads(message)
        
    def accept(self, sock, mask):
        """Accept new connection."""
        conn, addr = sock.accept()
        self.selelector.register(conn, selectors.EVENT_READ, self.read)

    def recv_msg(self, conn, mask):
        """Receive message from connection."""
        header = conn.recv(2)
        size = int.from_bytes(header, "big")
        message = conn.recv(size)
        
        if len(message) != 0:
            if conn in self.sockets.keys():
                serialization = self.sockets[conn]
            else:
                try:
                    if message.decode("utf-8").startswith("{"):
                        serialization = Serializer.JSON
                    else:
                        serialization = Serializer.XML
                except:
                    serialization = Serializer.PICKLE
                
            data = self.decode(message, serialization) 
            return data 
        return None
    
    def send(self,conn,message):
        """Send message to conn."""
        header = len(message).to_bytes(2, "big")
        conn.send(header + message)

    def getRootsTopics(self,topic)->list:
        """Get list of topics by recursive leaf."""
        roots=topic.split("/")
        topics=[]
        for i in range(len(roots)):
            root=""
            for ii in range(len(roots)-i):
                root+=(roots[ii])+"/"
            topics.append(root[:-1])
        return topics

    def read(self, conn, mask):
        """Read message from connection."""
        data = self.recv_msg(conn, mask)
        if data != None:
            if conn not in self.sockets.keys() and data["action"]=="format":
                self.sockets[conn] = Serializer.getSerializer(data["value"])

            elif data["action"]=="list_topics":
                message = self.encode(self.format("send",value=self.list_topics(), serialization=self.sockets[conn]), self.sockets[conn])
                self.send(conn,message)
            elif data["action"]=="subscribe":
                self.subscribe(data["topic"], conn, self.sockets[conn])
                for topic in self.topics.keys():
                    if data["topic"].startswith(topic):
                        last_value = self.get_topic(data["topic"])
                        if last_value != None:
                            message = self.encode(self.format("send", topic=data["topic"], value=last_value, serialization=self.sockets[conn]), self.sockets[conn])
                            self.send(conn,message)
            elif data["action"]=="cancel":
                self.unsubscribe(data["topic"], conn)
            elif data["action"]=="publish":
                self.put_topic(data["topic"], data["value"])
                topicsArray=self.getRootsTopics(data["topic"])
                for topic in topicsArray:
                    if topic in self.topics.keys():
                        for sub in self.topics[topic][0]:
                            try:
                                message = self.encode(self.format("send", topic=data["topic"], value=data["value"], serialization=sub[1]), sub[1])
                                self.send(sub[0],message)
                            except:
                                pass
        else:
            self.selelector.unregister(conn)
            conn.close()


    def run(self):
        """Run until canceled."""

        while not self.canceled:
            try:
                for key, mask in self.selelector.select():
                    callback = key.data
                    callback(key.fileobj, mask)
            except KeyboardInterrupt or socket.error:
                self.canceled = True
                self.socket.close()
                break

