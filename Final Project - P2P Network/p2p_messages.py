import json

class Message:
    def __init__(self, message_type, data):
        self.message_type = message_type 
        self.data = data

    def __str__(self):
        return json.dumps({"type": self.message_type, "data": self.data})


class Join_Request(Message):
    def __init__(self, node_ip, node_port):
        super().__init__("join_request", {"node_ip": node_ip, "node_port": node_port})
    
    @property
    def node_ip(self):
        return self.data["node_ip"]
    
    @property
    def node_port(self):
        return self.data["node_port"]

class Join_Ack(Message):
    def __init__(self, nodes):
        super().__init__("join_ack", {"nodes": nodes})       

    @property
    def nodes(self):
        return self.data["nodes"]

class Update_Nodes(Message):
    def __init__(self, node_ip, node_port, action):
        super().__init__("update_nodes", {"node_ip": node_ip, "node_port": node_port, "action": action})
    
class Solve_Sudoku(Message):
    def __init__(self, solutions):
        super().__init__("solve_sudoku", {"solutions": solutions})

class Send_Work(Message):
    def __init__(self, node_ip, node_port, range_to_distribute, solutions):
        data = {"node_ip": node_ip, "node_port": node_port, "range":range_to_distribute, "solutions":solutions}
        super().__init__("send_work",data)   

class Work_Ack(Message):
    def __init__(self, node_ip, node_port):
        data = {"node_ip": node_ip, "node_port": node_port}
        super().__init__("work_ack", data)    
        
class Solution_Found(Message):
    def __init__(self, node_ip, node_port, solution_index):
        data = {"node_ip": node_ip, "node_port": node_port, "solution_index": solution_index}
        super().__init__("solution_found", data)

class Work_Done(Message):
    def __init__(self, node_ip, node_port, range_to_distribute):
        data = {"node_ip": node_ip, "node_port": node_port, "range": range_to_distribute}
        super().__init__("work_done", data)

class Hello(Message):
    def __init__(self, node_ip, node_port, solved, validations, network):
        data = {"node_ip": node_ip, "node_port": node_port, "stats": {"solved": solved, "validations": validations}, "network": network}
        super().__init__("hello", data)

