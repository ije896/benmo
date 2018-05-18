# Node class
import queue as qu
from blockchain import *

class Node:
    def __init__(self, id):
        self.id = id
        self.queue = qu.Queue()
        self.blockchain = Blockchain()

    def startInput(self):
        pass

    def moneyTransfer(self, amount, credit_node):
        trans = Transaction(amount, self.id, credit_node)
        self.queue.put(trans)
