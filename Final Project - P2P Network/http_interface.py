from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import node
import time
class HTTPHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, node = None, **kwargs):
        self.node = node
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # Endpoint status
        if self.path == '/stats':
            # Envia resposta de status
            self.send_response(200)
            
            # Envia cabeçalhos
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response_message = self.node.getStats()
            
            # Envia mensagem de resposta
            self.wfile.write(bytes(json.dumps(response_message), "utf8"))

        # Endpoint network
        elif self.path == '/network':
            # Envia resposta de status
            self.send_response(200)
            
            # Envia cabeçalhos
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Mensagem de resposta
            response_message = self.node.getNetwork()
            
            # Envia mensagem de resposta
            self.wfile.write(bytes(json.dumps(response_message), "utf8"))
        else:
            # Envia resposta de status para recurso não encontrado
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes("Resource not found", "utf8"))

    def do_POST(self):  
        if self.path == '/solve':
            # Determina o comprimento dos dados
            content_length = self.headers['Content-Length']

            if content_length != None:
                print(f"Received POST request to {self.path}")
                content_length = int(content_length)

                post_data = self.rfile.read(content_length)
                
                # Verifica se o conteúdo é JSON
                if self.headers['Content-Type'] == 'application/json':
                    # Faz parse dos dados JSON
                    parsed_data = json.loads(post_data.decode('utf-8'))
 
                    # Se for o envio de um sudoku
                    if 'sudoku' in parsed_data:
                        sudoku = parsed_data['sudoku']
                        start=time.time()
                        sudoku_solution = self.node.handle_sudoku_request(sudoku)
                        timeExec=str(time.time()-start)
                        # Envia resposta de status
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        # Envia mensagem de resposta
                        self.wfile.write(bytes("\n"+json.dumps(sudoku_solution)+"\n"+timeExec+"\n", "utf8"))
                        return
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(bytes("Unsupported Media Type", "utf8"))
        else:
            # Envia resposta de status para tipo de contedo não suportado
            self.send_response(415)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes("Unsupported Media Type", "utf8"))
        return

class NodeHTTPInterface:
    def __init__(self, node):
        self.node = node
        self.port = node.http_Port

    def run(self):
        self.server_address = ('', self.port)
        self.httpd = ThreadingHTTPServer(self.server_address, lambda *args, **kwargs: HTTPHandler(*args, node = self.node, **kwargs))
        print(f'Starting httpd server on port {self.port}...')
        self.httpd.serve_forever()
    
    def close(self):
        pass
