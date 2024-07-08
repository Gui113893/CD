import argparse
import socket
import threading
import logging
import pickle
import json     
import http_interface
import p2p_messages
import p2p
import signal
import selectors
import sys
import time
from Generator import *
from queue import *
from multiprocessing import Queue as mpQueue
from temp import *

class Node():
    
    def __init__(self):
        # self.inputSudoku=[]
        self.http_Port = None
        self.p2p_Port = None
        self.anchor = None
        self.handicap = 0
        self.isSudoku_requested = False

        self.http_queue = Queue() 
        self.p2p_queue = mpQueue()  
        self.node_queue = Queue()  

        self.sel = selectors.DefaultSelector()
    
        self.stats = {}
        self.network = {}


    def getStats(self):
        return self.stats
    
    def getNetwork(self):
        return self.formatNetwork(self.network)

    def handle_sudoku_request(self, sudoku):
        """
        Quando é recebido um sudoku pelo http, são geradas as soluções que posteriormente vão ser passadas para a P2P Queue
        De seguida, a thread http fica em get da queue http até que a solução seja encontrada
        """
        self.isSudoku_requested = True
        print("Generating sudoku solutions")
        solutions = self.generateSolutions(sudoku)
        solution_index = self.http_queue.get(block=True)
        print("Solution found")
        return solutions[solution_index]

    def generateSolutions(self, sudoku):
        generator = Generator(sudoku)
        solutions = generator.generateSolutions()

        message = p2p_messages.Solve_Sudoku(solutions=solutions)
        print(f"Sending solutions to p2p queue for distribution")
        self.p2p_queue.put(message)
        return solutions
    
    def handle_p2p_queue(self, fileobj, mask):
        while not self.p2p_queue.empty():
            message = self.p2p_queue.get()
            message = json.loads(str(message))
            message_type = message["type"]
            data = message["data"]

            if message_type == "solve_sudoku":
                solutions = data["solutions"]
                print(f"Received solve_sudoku message")
                self.p2p_node.initial_distribute_checks(solutions)
            
            elif message_type == "solution_found":
                self.p2p_node.send_solution_found(data)
                
            elif message_type == "work_done":
                self.p2p_node.send_work_done(data)
                
    def check(self):
        message = self.node_queue.get(block=True)
        message = json.loads(str(message))
        message_type = message["type"]
        data = message["data"]
        print(f"Received {message_type} message")
        print("Inside check")
        if message_type == "send_work":
            node_ip = data["node_ip"]
            node_port = data["node_port"]
            range_to_distribute = data["range"]
            solutions = data["solutions"]
            
            is_valid = False
            print(f"Doing range {range_to_distribute}")
            for i in range(range_to_distribute[0], range_to_distribute[1] + 1):
                solution_to_check = solutions[i-range_to_distribute[0]]
                sudoku_solution = Sudoku(solution_to_check)

                # Converter o handicap de milissegundos para segundos
                handicap_seconds = self.handicap / 1000

                is_valid = sudoku_solution.check(base_delay=handicap_seconds, interval=10 ,threshold=1)
                print(f"Check index {i}")
                
                self.stats["all"]["validations"] += 1
                self.stats["nodes"][0]["validations"] += 1
                if is_valid:
                    self.stats["all"]["solved"] += 1
                    print(f"Solution found in node {self.p2p_node.address} in the index {i}")
                    msg = p2p_messages.Solution_Found(solution_index=i, node_ip=node_ip, node_port=node_port)
                    self.p2p_queue.put(msg)
                    break
            
            if is_valid == False:
                print(f"Work done in node {self.p2p_node.address} of range {range_to_distribute}")
                msg = p2p_messages.Work_Done(node_ip=node_ip, node_port=node_port, range_to_distribute=range_to_distribute)
                self.p2p_queue.put(msg)
        self.check()
        

    def init_http_interface(self):
        self.http_server = http_interface.NodeHTTPInterface(self)
        self.http_server.run()
    
    def init_p2p_interface(self):
        # Para além de inicializar a thread do p2p node, registamos a queue do p2p no selector para ficar á escuta de mensagens de outras threads
        self.sel.register(self.p2p_queue._reader.fileno(), selectors.EVENT_READ, self.handle_p2p_queue)
        self.p2p_node = p2p.P2PNode(self)
        
        # /stats info inicial
        self.stats = {"all": {"solved": 0, "validations": 0}, "nodes": [{"address": self.formatAddress(self.p2p_node.address), "validations": 0}]}

        self.p2p_node.run()
        
    def formatNetwork(self, network):
        network_formatted = {}
        for node, nodes in network.items():
            node_ip = node[0]
            node_port = node[1]
            key_formated = node_ip + ":" + str(node_port) # key : "ip:port"
            nodes_formated = []
            for n in nodes:
                nodes_formated.append(n[0] + ":" + str(n[1])) # nodes : "ip:port"
            network_formatted[key_formated] = nodes_formated
        return network_formatted

    def formatAddress(self, address):
        return address[0] + ":" + str(address[1])
    
    def isNodeInStats(self, node):
        for node_stats in self.stats["nodes"]:
            if node_stats["address"] == self.formatAddress(node):
                return True
        return False
 

    def run(self):
        self.http_thread = threading.Thread(target=self.init_http_interface)
        self.p2p_thread = threading.Thread(target=self.init_p2p_interface)
        self.check_thread = threading.Thread(target=self.check)

        self.http_thread.start()
        self.p2p_thread.start()
        self.check_thread.start()

        while True:
            events = self.sel.select(timeout=None)
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
                        
if __name__ == "__main__":
    node = Node()


    parser = argparse.ArgumentParser(description='Node', add_help=False)
    parser.add_argument('-p' , type=int, required=True, help='HTTP port') 
    parser.add_argument('-s', type=int, required=True, help='P2P port')
    parser.add_argument('-a', help='Anchor for a peer to connect if is not the first')
    parser.add_argument('-h',type=float, default=0, help='Handicap in miliseconds for the check()')
    args = parser.parse_args()

    if args.p:
        node.http_Port = args.p
    
    if args.s:
        node.p2p_Port = args.s

    if args.a:
        node.anchor = (str(args.a.split(':')[0]), int(args.a.split(':')[1])) # ip:port
    else:
        node.anchor = None
    
    if args.h:
        node.handicap = args.h

    node.run()
