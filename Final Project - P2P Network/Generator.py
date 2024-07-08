# import time

# start_time = time.time()
# def generate_permutations_with_repetition(nums, length):
#     result = [[]]
#     for _ in range(length):
#         new_result = []
#         for perm in result:
#             for num in nums:
#                 new_result.append(perm + [num])
#         result = new_result
#     return result

# # Exemplo de uso
# numbers = [1, 2, 3, 4, 5, 7, 8, 9]
# length = 8
# perms = generate_permutations_with_repetition(numbers, length)

# end_time = time.time()

# execution_time = end_time - start_time
# print("Tempo de execução:", execution_time, "segundos")
# # print(len(perms))
# # aaa=[1, 2, 3,4,5,7,8,9]
# # n=0
# # for i in range(len(aaa)):
# #     n+=aaa[-i-1]*10**i
# # print(n)
# def getPossibiliti(self):
#         num=81
#         for i in range(9):
#             for ii in range(9):
#                 if(self.grid[i][ii]!=0):
#                     num-=1

# def fatorial(n):
#     if n == 0:
#         return 1
#     else:
#         return n * fatorial(n-1)

# # Exemplo de uso:
# numero = 9
# resultado = fatorial(numero)
# print(f'O fatorial de {numero} é {resultado*9}')
# print(81**9)
# print(list({1:2}.keys()))
# HOST="localhost"
# from http.server import HTTPServer,BaseHTTPRequestHandler
# class one(BaseHTTPRequestHandler):
#     def do_GET(self):
#         self.send_response(200)
#         self.send_header("Content-type","text/html")
#         self.end_headers()
#         self.wfile.write(bytes("<html><body><h1>O mundo</h1></body></html>"),"utf-8")

# server=HTTPServer((HOST,8888),one)
# print(1)
# server.serve_forever()
# server.server_close()
# print(2)
# dicionario_original = {'a': 1, 'b': 2}
# dicionario_novo = {'b': 3, 'c': 4}

# # Atualizando o dicionário original com o dicionário novo
# dicionario_original.update(dicionario_novo)

# print(dicionario_original)
# # Convert the inner lists to tuples and then hash the tuple of these tuples
# matrix_tuple = tuple(tuple(row) for row in [
#     [0,0,0,1,0,0,0,0,0],
#     [0,0,0,3,2,0,0,0,0],
#     [0,0,0,0,0,9,0,0,0],
#     [0,0,0,0,0,0,0,7,0],
#     [0,0,0,0,0,0,0,0,0],
#     [0,0,0,9,0,0,0,0,0],
#     [0,0,0,0,0,0,9,0,0],
#     [0,0,0,0,0,0,0,0,3],
#     [0,0,0,0,0,0,0,0,0]
# ])
# print(abs(hash(matrix_tuple)%20000000))

# numero1 = 12340000
# numero2 = 12350000
# import time
# start=time.process_time()
# primos=contar_primos(abs(numero1),numero2)
# print("O número de primos até", numero1, "é:", primos)
# print(time.process_time()-start)

# num=1235
# const=12
# nodes=3
# rasao=int(num/const/nodes)
# lis=[(0,rasao)]
# lis.append((lis[-1][1]+1,lis[-1][1]+rasao))
# lis.append((lis[-1][1]+1,lis[-1][1]+rasao))
# lis.append((lis[-1][1]+1,lis[-1][1]+rasao))
# if lis[-1][1]>num:
#     lis.append((lis[-1][1],num))
# print(lis)

from sudoku import Sudoku
sudo= [[4, 9, 8, 3, 5, 1, 2, 6, 7], [5, 3, 2, 9, 7, 0, 8, 4, 1], [6, 1, 7, 8, 4, 2, 5, 3, 9], [3, 2, 5, 1, 8, 7, 4, 9, 6], [0, 7, 4, 6, 9, 3, 1, 5, 2], [1, 6, 9, 5, 2, 4, 3, 7, 8], [9, 4, 6, 2, 1, 5, 7, 8, 3], [7, 8, 1, 4, 3, 9, 6, 2, 5], [2, 5, 3, 7, 6, 8, 9, 1, 4]]
class Generator():
    def __init__(self,sudoku):
        self.sudoku = sudoku

    def findZeros(self):
        numZeros=[]
        for col in range(9):
            for row  in range(9):
                if(self.sudoku[col][row]==0):
                    numZeros.append((col,row))
        return numZeros
    
    def addNumToSudoku(self, list_sudoku,cord):
        result=[]
        for sudoku in list_sudoku:
            for i in range(1,10):
                clone_sudoku = [list(line) for line in sudoku]
                clone_sudoku[cord[0]][cord[1]]=i
                result.append(clone_sudoku)
        return result
    def generateSolutions(self):
        result=[self.sudoku]
        for cord in self.findZeros():
            result=self.addNumToSudoku(result,cord)
        return result
    
#for i in list(Generator(sudo).GerarSudokuList()):
 #   print(Sudoku(i))
