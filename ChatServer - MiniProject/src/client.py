import logging
import sys
import selectors
import fcntl
import os
import socket
from .protocol import CDProto

logging.basicConfig(filename=f"{sys.argv[0]}.log", level=logging.DEBUG)


class Client:
    """Chat Client process."""

    def __init__(self, name: str = "Foo"):
        """Initializes chat client."""
        self.server_address = ('', 2000) 
        self.current_channel = "main"
        self.sel = selectors.DefaultSelector()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name

    def connect(self):
        """Connect to chat server and setup stdin flags."""
        self.socket.connect(self.server_address)
        msg = CDProto.register(self.name)
        CDProto.send_msg(self.socket, msg)

    def send(self, stdin, mask):
        """Send message to server."""
        InMessage = stdin.read()
        InMessage = InMessage[:len(InMessage)-1]

        if InMessage:

            # Join message
            if InMessage[:6] == "/join ":
                # Added channel to the list
                channel = InMessage[6:]
                self.current_channel = channel
                msg = CDProto.join(channel)
                CDProto.send_msg(self.socket,msg)
            
            # Register message
            elif InMessage[:10] == "/register ":
                # Register the user
                self.name = InMessage[10:]
                msg = CDProto.register(self.name)
                CDProto.send_msg(self.socket,msg)

            # Text message
            else:

                if InMessage[:9] == "/message ":
                    InMessage = InMessage[9:]

                msg = CDProto.message(InMessage, self.current_channel)
                CDProto.send_msg(self.socket,msg)
                if msg.message == "exit":
                    sys.exit(0)
    
    def receive(self, sock, mask):
        """Receive message from server."""
        data = CDProto.recv_msg(sock)
        # If the message is not empty
        if data != "" and data != None:
            print("\n<<" + data.message)

    def loop(self):
        """Loop indefinitely."""
        # set sys.stdin none-blocking
        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

        self.sel.register(sys.stdin, selectors.EVENT_READ, self.send)
        self.sel.register(self.socket, selectors.EVENT_READ, self.receive)
        while True:
            sys.stdout.write(">>")
            sys.stdout.flush()
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

