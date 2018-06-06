# Node class
import queue as q
from blockchain import *
from message import *
import time, socket, os, sys

class Node:
    def __init__(self, id):
        self.id = id
        self.queue = q.Queue(10)
        self.blockchain = Blockchain()
        self.balance = 100
        self.round = 0
        self.accepted_block = None

    def startInput(self):
        action = input('Enter a command (send/print): ').lower().strip()
        if action=='send':
            amount = int(input('Enter an amount: ').lower().strip())
            credit_node = input('Enter destination for transaction(1-5): ').lower().strip() # maybe also int for enum?
            self.moneyTransfer(amount, credit_node)
        if action=='print':
            self.printAll()

    def moneyTransfer(self, amount, credit_node):
        if self.balance>amount:
            trans = Transaction(amount, self.id, credit_node)
            self.queue.put(trans)
        else:
            print("Insufficient funds")

    def checkQueuePerUnitTime(self, time_in_seconds):
        while True:
            if not self.queue.empty(): # and you're not already in proposal state
                # start proposal phase
                pass
            time.sleep(time_in_seconds)

    def printAll(self):
        self.printBalance()
        self.printQueue()
        self.printBlockchain()

    def printBlockchain(self):
        print("Node blockchain: ", self.blockchain)

    def printBalance(self):
        print("Node balance: ", self.balance)

    def printQueue(self):
        l = list(self.queue)
        print("Node queue: ", l)

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
        if self.accepted_block:
            # send promise with block
            pass
        # send promise w/o value
        pass


    def promiseHandler(self, conn, message):
        self.promises+=1 # member variable?
        if self.promises >= majority:
            # broadcast accept
            pass
        pass

    def acceptHandler(self, conn, message):
        if message.round <= self.round:
            # nack
            pass
        if message.depth <= self.blockchain.depth:
            # nack
            pass
        self.accepted_block = message.block
        # broadcast accepted
        pass

    def acceptedHandler(self, conn, message):
        if True: # ACTUALLY --> self.state = PROPOSER:
            self.acceptances+=1 # member variable?
            if self.acceptances >= majority:
                # reset acceptances, promises
                self.queue = q.Queue()
                self.updateFromBlock(self.accepted_block) # SHOULD be the proposed block
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
        self.updateFromBlock(self.accepted_block, message.depth)
        # reset vars
        pass

    def sendMessage(self, message):
        pass
    def broadcast(self, message):
        pass

    def updateFromBlock(self, block, depth):
        self.blockchain.addBlock(block)
        for trans in len(self.blockchain[depth].transactions):
            if trans.credit_node == self.id:
                self.balance+=trans.amount
            if trans.debit_node == self.id:
                self.balance-=trans.amount
        pass
