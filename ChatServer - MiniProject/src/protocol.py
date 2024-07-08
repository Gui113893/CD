"""Protocol for chat server - Computação Distribuida Assignment 1."""
import json
from datetime import datetime
from socket import socket


class Message:
    """Message Type."""
    def __init__(self, command: str):
        self.command = command

    
class JoinMessage(Message):
    """Message to join a chat channel."""
    def __init__(self, command: str, channel: str):
        super().__init__(command)
        self.channel = channel

    def __str__(self) -> str:
        """Converts object to JSON."""
        return f'{{"command": "{self.command}", "channel": "{self.channel}"}}'


class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, command: str, user: str):
        super().__init__(command)
        self.user = user

    def __str__(self) -> str:
        """Converts object to JSON."""
        return f'{{"command": "{self.command}", "user": "{self.user}"}}'

    
class TextMessage(Message):
    """Message to chat with other clients."""
    def __init__(self, command: str, message: str, channel: str = None, ts:int = None):
        super().__init__(command)
        self.message = message
        self.channel = channel
        self.ts = ts

    def __str__(self) -> str:
        """Converts object to JSON."""
        if self.channel:
            return f'{{"command": "{self.command}", "message": "{self.message}", "channel": "{self.channel}", "ts": {self.ts}}}'

        return f'{{"command": "{self.command}", "message": "{self.message}", "ts": {self.ts}}}'


class CDProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def register(cls, username: str) -> RegisterMessage:
        """Creates a RegisterMessage object."""
        return RegisterMessage("register", username)

    @classmethod
    def join(cls, channel: str) -> JoinMessage:
        """Creates a JoinMessage object."""
        return JoinMessage("join", channel)

    @classmethod
    def message(cls, message: str, channel: str = None) -> TextMessage:
        """Creates a TextMessage object."""
        return TextMessage("message", message, channel, int(datetime.now().timestamp()))

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        """Sends through a connection a Message object."""
        
        jsonMessage = json.dumps(str(msg))

        # Get header of the message 
        h = len(jsonMessage).to_bytes(2,'big')

        # Send the message to the server
        connection.send(h + jsonMessage.encode('utf-8'))

    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        """Receives through a connection a Message object."""

        # Read the header of the message
        h = int.from_bytes(connection.recv(2),'big')

        if h == 0:
            return None
        
        message = connection.recv(h).decode('utf-8')

        try:
            jsonMessage = json.loads(message)

            if type(jsonMessage) is not dict:
                jsonToDict = json.loads(jsonMessage)
            
            else:
                jsonToDict = jsonMessage
        
        except json.JSONDecodeError:
            raise CDProtoBadFormat(message)

               
        if jsonToDict["command"] == "register":
            user = jsonToDict["user"]
            return CDProto.register(user)

        elif jsonToDict["command"] == "join":
            channel = jsonToDict["channel"]
            return CDProto.join(channel)
        
        elif jsonToDict["command"] == "message":
            msg = jsonToDict["message"]

            # Check if the channel atribute exists
            try:
                channel = jsonToDict["channel"]
            except KeyError:
                return CDProto.message(msg)
            
            return CDProto.message(msg,channel)


class CDProtoBadFormat(Exception):
    """Exception when source message is not CDProto."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")
