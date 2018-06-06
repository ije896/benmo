# Node class
import queue as q
from blockchain import *
from message import *

# highest proposed round num
# expected value

class Node:
    def __init__(self, id):
        self.id = id
        self.queue = q.Queue()
        self.blockchain = Blockchain()
        self.balance = 100
        self.round = 0
        self.accepted = None

    def startInput(self):
        pass

    def moneyTransfer(self, amount, credit_node):
        # if credit is high enough
        trans = Transaction(amount, self.id, credit_node)
        self.queue.put(trans)

    def printBlockchain(self):
        pass

    def printBalance(self):
        pass

    def printQueue(self):
        pass

    def startListening(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((TCP_IP, TCP_PORT))
        s.listen(5)

        while True:
            conn, addr = s.accept()
            data = conn.recv(buffer_size)
            message = m.decode_message(data)
            if message.type == PREPARE:
                pass
            elif message.type == PROMISE:
                pass
            elif message.type == ACCEPT:
                pass
            elif message.type == ACCEPTED:
                pass
            elif message.type == DECISION:
                pass

            thread = Thread(target=self.process_message, args=(conn, ))
            tname = thread.getName()
            thread.daemon = True
            thread.start()
