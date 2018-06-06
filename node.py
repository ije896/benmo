# Node class
import queue as q
from blockchain import *
from message import *

class Node:
    def __init__(self, id):
        self.id = id
        self.queue = q.Queue()
        self.blockchain = Blockchain()
        self.balance = 100
        self.round = 0
        self.accepted_value = None

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
                startWorker(self.prepareHandler, conn, message)
            elif message.type == PROMISE:
                startWorker(self.promiseHandler, conn, message)
            elif message.type == ACCEPT:
                startWorker(self.acceptHandler, conn, message)
            elif message.type == ACCEPTED:
                startWorker(self.acceptedHandler, conn, message)
            elif message.type == DECISION:
                startWorker(self.decisionHandler, conn, message)

    def startWorker(self, target, conn, message):
        thread = Thread(target=target, args=(conn, message, ))
        tname = thread.getName()
        thread.daemon = True
        thread.start()

    def prepareHandler(self, conn, message):
        if message.round <= self.round:
            # nack
            pass
        if message.depth <= self.blockchain.depth:
            # nack
            pass
        if self.acceptedValue:
            # send promise with value
            pass
        # send promise w/o value
        pass


    def promiseHandler(self, conn, message):
        self.promises++ # member variable?
        if self.promises >= majority:
            # close promise handle
            # broadcast accept
            pass

    def acceptHandler(self, conn, message):
        if message.round <= self.round:
            # nack
            pass
        if message.depth <= self.blockchain.depth:
            # nack
            pass
        self.acceptedValue = message.value
        # broadcast accepted
        pass

    def acceptedHandler(self, conn, message):
        if self.state = PROPOSER:
            self.acceptances++ # member variable?
            if self.acceptances >= majority:
                # reset acceptances, promises
                self.queue = q.Queue()
                # add block to blockchain
                # broadcast decision
                pass
            pass
        pass

    def decisionHandler(self, conn, message):
        if message.round <= self.round:
            # nack
            pass
        if message.depth <= self.blockchain.depth:
            # nack
            pass
        # add block to blockchain
        # reset vars
        pass
