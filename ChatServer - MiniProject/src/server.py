import logging
import selectors
import socket
from .protocol import CDProto, CDProtoBadFormat

"""CD Chat server program."""

logging.basicConfig(filename="server.log", level=logging.DEBUG)


class Server:
    """Chat Server process."""

    def __init__(self):

        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = ('', 2000)
        self.socket.bind(self.server_address)
        self.socket.listen(50)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Selector setup
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ, self.accept)

        # Channels, main channel is the default
        self.channels = {"main": []}

    def accept(self, sock, mask):
        """Accept new client connections."""
        client_socket, client_address = sock.accept()
        print(f"SERVER: Connection from {client_address}")
        client_socket.setblocking(False)
        self.sel.register(client_socket, selectors.EVENT_READ, self.receive)

    def receive(self, client_socket, mask):
        """Receive data from the client."""
        try:
            data = CDProto.recv_msg(client_socket) # Receive message
        except CDProtoBadFormat:
            print("SERVER: Bad Format Error")
            return

        if data:

            # Process Register
            if(data.command == "register"):
                # Add user to the main channel
                self.channels["main"].append(client_socket)

            # Process Join
            elif(data.command == "join"):
                # Remove user from the current channel
                for channel in self.channels:
                    if client_socket in self.channels[channel]:
                        self.channels[channel].remove(client_socket)
                        break

                # Check if the channel exists
                if data.channel in self.channels:
                    # Add user to the channel
                    self.channels[data.channel].append(client_socket)
                else:
                    # Create a new channel
                    self.channels[data.channel] = [client_socket]

            # Process message
            elif(data.command == "message"):
                # Exit message
                if data.message == "exit":
                    self.terminate(client_socket)

                # Check if the atribute channel exists
                elif data.channel:
                    for client in self.channels[data.channel]:
                        CDProto.send_msg(client,data)
                else:
                    for client in self.channels["main"]:
                        CDProto.send_msg(client,data) # Send the message to all users  

                
        else:
            self.terminate(client_socket)

    def terminate(self, client_socket):
        for channel in self.channels:
            if client_socket in self.channels[channel]:
                self.channels[channel].remove(client_socket)
                break
        self.sel.unregister(client_socket)
        client_socket.close()

    def loop(self):
        """Loop indefinitely."""
        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
