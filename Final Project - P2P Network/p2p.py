import socket
import threading
import json
import selectors
import p2p_messages
import time
import math
from time import monotonic

class P2PNode():
    def __init__(self, node):
        self.node = node
        self.port = node.p2p_Port
        self.address = ('127.0.0.1', self.port) # Adress para comunicar na rede
        self.anchor = node.anchor

        # Lista de nodes conhecidos [(ip, port): socket_for_connection, ...]
        self.network_nodes = {}

        # Lista de nodes disponiveis para atribuir tarefas
        self.available_nodes = [self.address]

        # Dicionário com os ranges atribuidos a cada node
        self.distributed_ranges = {}

        # Dicionário para guardar os tempos de hellos dos nodes
        self.hello_times = {}


        self.atribute_solution_count=0

        # Selector
        self.sel = selectors.DefaultSelector()

        self.start()

    def start(self):
        """
        Inicializa o node;
        Se ele é o primeiro nó da rede fica á espera de connections
        Se ele tem uma anchor associada, liga-se a ela
        """
        # Se é o primeiro nó da rede
        if self.anchor == None:
            self.listen()
        else:
            self.connect_to_anchor(self.anchor)
        
    def listen(self):
        # Cria o socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.address)
        self.sock.listen(10)
        self.sock.setblocking(False)
        self.sel.register(self.sock, selectors.EVENT_READ, self.accept_connection)
        print(f"Node {self.address} is listening for P2P connections...")
    
    def accept_connection(self, sock, mask):
        """
        Aceita a conexão de um node e cria um socket temporário TCP para comunicação com esse node:
            - socket_for_con: o socket para a comunicação
            - address: o address (ip, port) gerado dessa comunicação
        Ou seja, cada vez que um socket tenta comunicar com outro, é feito um canal de comunicação
        """
        socket_for_con, address = sock.accept()
        socket_for_con.setblocking(False)
        self.sel.register(socket_for_con, selectors.EVENT_READ, self.read_message)
    
    def connect_to_anchor(self, anchor):
        """
        Conecta-se á anchor:
            - anchor: (ip, port)
        """
        socket_to_anchor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_to_anchor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_to_anchor.connect(anchor)
        socket_to_anchor.setblocking(False)

        # Põe a anchor no seu dicionário network_nodes
        self.network_nodes[anchor] = socket_to_anchor
        self.available_nodes.append(anchor)
        
        # Manda um join request á anchor
        join_request = p2p_messages.Join_Request(self.address[0], self.address[1])
        self.send_message(socket_to_anchor, join_request)
        self.sel.register(socket_to_anchor, selectors.EVENT_READ, self.read_message)
        print(f"Sent a join request to anchor {anchor}")
    

    def send_message(self, connection, message):
        """
        Envia uma mensagem para um node:
            - connection: socket
            - message: Message
        """
        message = str(message)
        header = len(message).to_bytes(4, 'big')
        connection.send(header + message.encode("utf-8"))
    
    def recv_msg(self, connection, mask):
       try:
           connection.settimeout(3)  # Timeout de 3 segundos
           header = connection.recv(4)
           if not header:
               raise socket.timeout("No data received")
           size = int.from_bytes(header, "big")
           message = connection.recv(size).decode("utf-8")
           return json.loads(message)
       except socket.timeout:
           return None
       except Exception as e:
           print(f"Error reading message, maybe Node disconnected: {e}")
           return None
    
    def read_message(self, connection, mask):
        """
        Trata a mensagem recebida:
            - connection: socket
            - message: Message
        
        - Se o tipo da mensagem é um join_request, manda um join_ack com a lista de network_nodes conhecidos
        - Se o tipo da mensagem é um join_ack, manda, para todos dessa lista, um update_nodes com a sua informação
        - Se o tipo da mensagem é um update_nodes, adiciona á sua lista o node que vem em data 
        - Se o tipo da mensagem é um send_work, manda um work_ack e passa a mensagem para sua node queue para trabalhar
        - Se o tipo da mensagem é um solution_found, guarda a solução encontrada e põe na queue http
        - Se o tipo da mensagem é um work_done, tira o node dos available_nodes, tira o range dele dos distributed_ranges e redistribui o trabalho
        - Se o tipo da mensagem é um hello, guarda o tempo que o node demorou desde o ultimo hello e guarda a informação relevante ao /stats e ao /network
        """
        try:   
            message_decoded = self.recv_msg(connection, mask)
            print(f"Received message: {message_decoded}")
            if message_decoded == None:
                self.close_connection(connection)
                return

            message_type = message_decoded["type"]
            data = message_decoded["data"]

            if message_type == "join_request":
                node_to_send_reply = (data["node_ip"], data["node_port"]) # (ip:port)
                self.send_join_ack(origin=connection, to=node_to_send_reply)

            elif message_type == "join_ack":

                for node in data["nodes"]:
                    self.network_nodes[tuple(node)] = None

                self.send_update_nodes("insert")

            elif message_type == "update_nodes":

                print(f"Update nodes received to {data['action']} the node {data['node_ip']}:{data['node_port']}")
                node = (data["node_ip"], data["node_port"])
                
                if data["action"] == "insert":
                    self.network_nodes[node] = connection
                    self.available_nodes.append(node)
                    self.redistribute_work()

                    print("Avaiable nodes : ", self.available_nodes)
                elif data["action"] == "remove":
                    self.network_nodes.pop(node)

                print(f"The network nodes that I know: {[key for key in self.network_nodes.keys()]}")
            
            elif message_type == "send_work":
                node = (data["node_ip"], data["node_port"])
                range_to_distribute = data["range"]
                solutions = data["solutions"]
                msg = p2p_messages.Send_Work(node[0], node[1], range_to_distribute, solutions)
                self.node.node_queue.put(msg)
                msg = p2p_messages.Work_Ack(self.address[0], self.address[1])
                self.send_message(connection, msg)

            elif message_type == "solution_found":
                self.node.isSudoku_requested = False
                solution_index = data["solution_index"]
                node = (data["node_ip"], data["node_port"])
                self.available_nodes.append(node)

                for range_key, node_assigned in self.distributed_ranges.items():
                    if node == node_assigned:
                        self.distributed_ranges.pop(range_key)
                        break

                self.node.http_queue.put(solution_index)
                print(f"Solution found by {node}")
                print(f"Available nodes: {self.available_nodes}")
                print(f"Distributed ranges: {self.distributed_ranges}")
                print(f"Network nodes: {self.network_nodes}")

            elif message_type == "work_done":
                range_to_distribute = tuple(data["range"])
                node_done = self.distributed_ranges[range_to_distribute]
                print(f"Node done: {node_done}")
                self.available_nodes.append(node_done)
                self.distributed_ranges.pop(range_to_distribute)
                print(f"Available nodes: {self.available_nodes}")
                print(f"Distributed ranges: {self.distributed_ranges}")
                self.redistribute_work()
            
            elif message_type == "work_ack":
                node = (data["node_ip"], data["node_port"])
                print(f"Node {node} send a work ack")
            
            elif message_type == "hello":
                node = (data["node_ip"], data["node_port"])
                self.hello_times[node] = monotonic()

                # Caso o número de solved seja maior do que o meu, atualizar o meu número de solved
                if data["stats"]["solved"] > self.node.stats["all"]["solved"]:
                    self.node.stats["all"]["solved"] = data["stats"]["solved"]
                
                if not self.node.isNodeInStats(node):
                    self.node.stats["nodes"].append({"address": self.node.formatAddress(node), "validations": data["stats"]["validations"]})
                    self.node.stats["all"]["validations"] += data["stats"]["validations"]
                else:
                    for node_stats in self.node.stats["nodes"]:
                        if node_stats["address"] == self.node.formatAddress(node):
                            self.node.stats["all"]["validations"] -= node_stats["validations"]
                            node_stats["validations"] = data["stats"]["validations"]
                            self.node.stats["all"]["validations"] += node_stats["validations"]
                            break

                # Atualizar o /network
                self.node.network[node] = data["network"]
                self.node.network[self.address] = list(self.network_nodes.keys())

            else:
                print("Invalid message type")
                return

        except Exception as e:
            print(f"Error inside read_message: {e}")
            self.close_connection(connection)
            return

    def send_join_ack(self, origin, to):
        """
        Envia um join_ack para um node:
            - origin: socket da comunicação entre os nodes
            - to: (ip, port)
        """
        network_nodes_list = [key for key in self.network_nodes.keys()]
        join_ack = p2p_messages.Join_Ack(network_nodes_list)
        self.send_message(origin, join_ack)
        print(f"Sent a join ack to {to}")
    
    def send_update_nodes(self, action, node_ip = None, node_port = None):
        """
        Envia um update_nodes para cada node da network_nodes
        """
        if action != "insert" and action != "remove":
            raise ValueError("Invalid action")

        if node_ip == None or node_port == None:
            node_ip = self.address[0]
            node_port = self.address[1]

        update_nodes = p2p_messages.Update_Nodes(node_ip, node_port, action)
        for node in self.network_nodes.keys():
            node_connection = self.network_nodes[node]

            if node_connection == None:
                # Make the connection socket
                node_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                node_connection.connect(node)
                node_connection.setblocking(False)
                self.sel.register(node_connection, selectors.EVENT_READ, self.read_message)
                self.network_nodes[node] = node_connection

            self.send_message(node_connection, update_nodes)
            
            print(f"Sent an update nodes to {node} to {action} the node {node_ip}:{node_port}")
        print(f"The network nodes that I know: {[key for key in self.network_nodes.keys()]}")
        
        if action == "insert" and node_ip == self.address[0] and node_port == self.address[1]:
            self.listen() 

    def initial_distribute_checks(self, solutions):
        """
        Faz a distribuição inicial de trabalhos entre os nodes
            - solutions: lista de soluçoes
        """
        self.distributed_ranges = {}
        self.solutions = solutions
        numSolutions = len(solutions)-1
        const = 3
        numNodes = 1+len(self.network_nodes)
        self.atribute_solution_count=0
        
        # ratio = int(numSolutions/const/numNodes)
        ratio = int(numSolutions/const**(int(math.log10(numSolutions)+0.5))/numNodes)
        print(ratio)
        if ratio == 0:
            ratio = 1
        if ratio>320:
            ratio=300
        

        print(f"Distributed ranges calculated: {self.distributed_ranges}")
        for network_node in self.network_nodes:
            range_to_distribute = None
            if self.atribute_solution_count < numSolutions:

                end = min(self.atribute_solution_count + ratio, numSolutions)
                range_to_distribute=(self.atribute_solution_count, end)
                self.atribute_solution_count=end+1

            print("Avaiable nodes before assigning: ", self.available_nodes)
            if range_to_distribute is not None:
                self.distributed_ranges[range_to_distribute] = network_node
                print("Node to remove from availables: ", network_node)
                self.available_nodes.remove(network_node)
                self.send_work(network_node, range_to_distribute, solutions[range_to_distribute[0]:range_to_distribute[1]+1])
            print("Avaiable nodes after assigning: ", self.available_nodes)
        
        range_to_distribute = None
        if self.atribute_solution_count < numSolutions:
            end = min(self.atribute_solution_count + ratio, numSolutions)
            range_to_distribute=(self.atribute_solution_count, end)
            self.atribute_solution_count=end+1

        if range_to_distribute is not None:
            self.distributed_ranges[range_to_distribute] = self.address
            msg = p2p_messages.Send_Work(self.address[0], self.address[1], range_to_distribute, solutions[range_to_distribute[0]:range_to_distribute[1]+1])
            self.node.node_queue.put(msg)

    def send_work(self, node, range_to_distribute, solutions):
        """
        Envia um send_work para um node
            - node: (ip, port)
            - range_to_distribute: (start, end)
            - solutions: lista de soluçoes filtrada pelo range
        Caso o work seja mandado para o próprio nó, ele põe diretamente na sua node queue 
        """
        msg = p2p_messages.Send_Work(self.address[0], self.address[1], range_to_distribute, solutions)
        if node == self.address:
            print(f"Putting message in my node queue")
            self.node.node_queue.put(msg)
        else:
            print(f"Sending work to {node}")
            self.send_message(self.network_nodes[node], msg)
    
    def send_hello(self):
        msg = p2p_messages.Hello(self.address[0], self.address[1], self.node.stats["all"]["solved"], self.node.stats["nodes"][0]["validations"], list(self.network_nodes.keys()))
        for node in self.network_nodes.keys():
            #print(f"Sending hello to {node}")
            self.send_message(self.network_nodes[node], msg)

    def send_solution_found(self, data):
        node = (data["node_ip"], data["node_port"])
        if node == self.address:
            self.node.isSudoku_requested = False
            solution_index = data["solution_index"]
            for range_key, node_assigned in self.distributed_ranges.items():
                if node == node_assigned:
                    self.distributed_ranges.pop(range_key)
                    break
            print(f"Solution found by me")
            print(f"Available nodes: {self.available_nodes}")
            print(f"Distributed ranges: {self.distributed_ranges}")
            print(f"Network nodes: {self.network_nodes}")
            self.node.http_queue.put(solution_index)
        else:
            msg = p2p_messages.Solution_Found(self.address[0], self.address[1], data["solution_index"])
            self.send_message(self.network_nodes[node], msg)
    
    def send_work_done(self, data):
        node = (data["node_ip"], data["node_port"])
        msg = p2p_messages.Work_Done(data["node_ip"], data["node_port"], data["range"])
        range_key = tuple(data["range"])
        if node == self.address:
            self.available_nodes.append(self.address)
            self.distributed_ranges.pop(range_key)
            self.redistribute_work()
        else:
            self.send_message(self.network_nodes[node], msg)

    def redistribute_work(self):
        print(f"Sudoku requested: {self.node.isSudoku_requested}")
        if self.node.isSudoku_requested:
            print(f"Redistributing work to {self.available_nodes}")
            numSolutions = len(self.solutions)-1
            const = 3
            numNodes = 1+len(self.network_nodes)
            
            # ratio = int(numSolutions/const/numNodes)
            ratio = int(numSolutions/const**(int(math.log10(numSolutions)+0.5))/numNodes)
            
            print(ratio)
            if ratio == 0:
                ratio = 1
            if ratio>320:
                ratio=300

            for node in self.available_nodes:
                if self.atribute_solution_count<numSolutions:
                    end = min(self.atribute_solution_count + ratio, numSolutions)
                    self.distributed_ranges[(self.atribute_solution_count, end)] = None
                    self.atribute_solution_count=end+1

                for range_to_distribute in self.distributed_ranges.keys():
                    if self.distributed_ranges[range_to_distribute] == None:
                        self.distributed_ranges[range_to_distribute] = node
                        self.available_nodes.remove(node)
                        self.send_work(node, range_to_distribute, self.solutions[range_to_distribute[0]:range_to_distribute[1]+1])
                        break

    def close_connection(self, connection):
        """
        Fecha uma conexão:
            - connection: socket
        """
        
        try:
            self.sel.unregister(connection)
            for key, value in self.network_nodes.items():
                if connection == value:
                    for keyDR, valDR in self.distributed_ranges.items():
                        if valDR == key:
                            self.distributed_ranges[keyDR]=None
                    self.network_nodes.pop(key)
                    self.node.network.pop(key)
                    self.redistribute_work()
                    if key in self.available_nodes:
                        self.available_nodes.remove(key)
                    break
        except KeyError:
            pass
        connection.close()

    def run(self):
        start = monotonic()
        while True:
            events = self.sel.select(timeout=1)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
            
            if monotonic() - start > 5:
                self.send_hello()
                start = monotonic()
            
            for node, time in self.hello_times.items():
                if monotonic() - time > 20:
                    if node in self.network_nodes:
                        self.close_connection(self.network_nodes[node])
                        print(f"Node {node} disconnected - Hello Timeout")

    





    