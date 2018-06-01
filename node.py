# Node class
import queue as q
from blockchain import *
import message as m
import time, socket, os, sys
from threading import Thread
from message import MessageType as mt

from config import *


# TODO: is majority a const, 3, or is it dynamic as nodes go on/offline
# TODO: if dynamic, do we let the other nodes know when one goes offline/alrt for changes in cluster size?
MAJORITY = 3


class Node:
    def __init__(self, id, ip=None, port=None):
        self.id = id
        self.queue = q.Queue(10)
        self.blockchain = Blockchain()
        self.balance = 100

        self.ip = ip
        self.port = port

        self.latest_round = 0

        # state for acceptor phase -- resets after a decision is received
        self.accepted_block = None

        # state for proposer phase -- resets after decision is sent
        self.promises = 0
        self.acceptances = 0
        self.proposed_depth = 0
        self.proposed_round = 0
        self.proposed_block = None


    def startInput(self):
        action = input('Enter a command (send/print): ').lower().strip()
        if action=='send':
            amount = int(input('Enter an amount: ').lower().strip())
            credit_node = input('Enter destination for transaction(1-5): ').lower().strip() # maybe also int for enum?
            self.moneyTransfer(amount, credit_node)
        if action=='print':
            self.print_all()

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

    def print_all(self):
        self.print_balance()
        self.print_queue()
        self.print_blockchain()

    def print_blockchain(self):
        print("Node blockchain: ", self.blockchain)

    def print_balance(self):
        print("Node balance: ", self.balance)

    def print_queue(self):
        l = list(self.queue)
        print("Node queue: ", l)



    def startListening(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.ip, self.port))
        s.listen(5)

        while True:
            conn, addr = s.accept()
            data = conn.recv(BUFFER_SIZE)
            message = m.decode_message(data)
            if message.type == mt.PREPARE:
                self.startWorker(self.rcv_prepare, conn, message)
            elif message.type == mt.PROMISE:
                self.startWorker(self.rcv_promise, conn, message)
            elif message.type == mt.ACCEPT:
                self.startWorker(self.rcv_accept, conn, message)
            elif message.type == mt.ACCEPTED:
                self.startWorker(self.rcv_acceptance, conn, message)
            elif message.type == mt.DECISION:
                self.startWorker(self.rcv_decision, conn, message)

    def startWorker(self, target, conn, message):
        thread = Thread(target=target, args=(conn, message, ))
        tname = thread.getName()
        thread.daemon = True
        thread.start()


    def rcv_prepare(self, conn, message):
        if message.round <= self.latest_round:
            nack = m.Message(mt.NACK)
            self.send_message(conn, nack)
            return

        if message.depth <= self.blockchain.depth:
            nack = m.Message(mt.NACK)
            self.send_message(conn, nack)
            return

        if self.accepted_block:
            # send promise with block
            promise = m.Message(mt.PROMISE)
            self.send_message(conn, promise)
            return

        # send promise w/o value
        promise = m.Message(mt.PROMISE)
        self.send_message(conn, promise)


    def rcv_promise(self, conn, message):
        self.promises+=1 # member variable?
        if self.promises >= MAJORITY:
            # broadcast accept
            conn.close()
            accept = m.Message(mt.ACCEPT)
            self.broadcast_message(accept)


    def rcv_accept(self, conn, message):
        if message.round <= self.latest_round:
            nack = m.Message(mt.NACK)
            self.send_message(conn, nack)
            return

        if message.depth <= self.blockchain.depth:
            nack = m.Message(mt.NACK)
            self.send_message(conn, nack)
            return

        self.accepted_block = message.block
        # broadcast accepted
        accepted = m.Message(mt.ACCEPTED)
        self.broadcast_message(accepted)


    def rcv_acceptance(self, conn, message):
        if message.proposer_id == self.id:
            self.acceptances += 1
            if self.acceptances >= MAJORITY:
                # TODO: implement buffer queue for transactions entered after proposer phase begins
                self.updateFromBlock(self.proposed_block, self.proposed_depth)

                decision = m.Message(mt.DECISION,
                                     proposer_id=self.id,
                                     depth=self.proposed_depth,
                                     round=self.proposed_round,
                                     block=self.proposed_block
                                     )

                self.reset_proposer_state()



    def rcv_decision(self, conn, message):
        if message.round <= self.latest_round:
            nack = m.Message(mt.NACK)
            self.send_message(conn, nack)
            return
        if message.depth <= self.blockchain.depth:
            nack = m.Message(mt.NACK)
            self.send_message(conn, nack)
            return
        self.updateFromBlock(message.block, message.depth)
        self.reset_acceptor_state()



    def sendMessage(self, message, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # time.sleep(SLEEP_TIME)
        sock.connect((ip, port))
        # print("Was able to send message: ", message)
        message = m.encode_message(message)
        sock.send(message)

        # data = sock.recv(BUFFER_SIZE)
        sock.close()
        # print("Server %d SENT an update" )
        pass


    def send_message(self, conn, message):
        message = m.encode_message(message)
        conn.send(message)
        conn.close()

    def broadcast_message(self, message):
        for i in range(len(ip_addrs)):
            if not i == self.id:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((ip_addrs[i], ports[i]))
                self.send_message(sock, message)

    def updateFromBlock(self, block, depth):
        self.blockchain.addBlock(block)
        for trans in self.blockchain.blocks[depth].transactions:
            if trans.credit_node == self.id:
                self.balance+=trans.amount
            if trans.debit_node == self.id:
                self.balance-=trans.amount
        pass


    def reset_proposer_state(self):
        self.acceptances = 0
        self.promises = 0
        self.proposed_block = None
        self.queue = q.Queue()

    def reset_acceptor_state(self):
        self.accepted_block = None