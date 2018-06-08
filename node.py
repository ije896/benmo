# Node class
import queue as q
from blockchain import *
import message as m
import time, socket, os, sys
from threading import Thread
from message import MessageType as mt
from enum import IntEnum

from config import *


# TODO: is majority a const, 3, or is it dynamic as nodes go on/offline
# TODO: if dynamic, do we let the other nodes know when one goes offline/alert for changes in cluster size?
MAJORITY = 2
NUM_NODES = 3

# Proposer phase
class pp(IntEnum):
    NONE = 0
    PREPARE = 1
    ACCEPT = 2
    DECISION = 3

class qs(IntEnum):
    EMPTY = 0
    NONEMPTY = 1

# Acceptor phase
# TODO: Should acceptor phases be a key value for id-phase? can you be in different phases w.r.t. different proposers?
class ap(IntEnum):
    NONE = 0
    PROMISE = 1
    ACCEPTED = 2

# Node phase
class np(IntEnum):
    OFFLINE = 0
    ONLINE = 1


class Node:
    def __init__(self, id, propose_cooldown=7):
        self.id = id
        self.queue = q.Queue(10)
        self.blockchain = Blockchain()
        self.balance = 100

        self.ip = ip_addrs[id]
        self.port = ports[id]

        self.latest_round = 0

        # state for acceptor phase -- resets after a decision is received
        self.accepted_block = None
        self.acceptor_phase = ap.NONE

        # state for proposer phase -- resets after decision is sent
        self.promises = 0
        self.acceptances = 0
        self.proposed_depth = 0
        self.proposed_round = 0
        self.proposed_block = None
        self.proposer_phase = pp.NONE

        self.propose_cooldown = propose_cooldown

        self.queue_state = qs.EMPTY

        self.listen_socket = None

        self.startListeningThread()
        self.startInput()


    def startInput(self):
        while (True):
            action = input('Enter a command (send/print): ').lower().strip()
            if action=='send':
                amount = int(input('Enter an amount: ').lower().strip())
                credit_node = input('Enter destination for transaction(1-5): ').lower().strip() # maybe also int for enum?
                self.moneyTransfer(amount, credit_node)
            if action=='print':
                self.print_all()
            if action=='safe close':
                self.listen_socket.close()
                exit(0)


    def moneyTransfer(self, amount, credit_node):
        if self.balance>amount:

            if self.queue.qsize() == 0:
                self.queue_state = qs.NONEMPTY
                self.start_proposer_loop_thread()

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
        l = self.queue_to_list(self.queue)
        print("Node queue: ", l)


    def startListeningThread(self):
        thread = Thread(target=self.startListening, args=())
        tname = thread.getName()
        thread.daemon = True
        thread.start()

    def startListening(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.ip, self.port))
        s.listen(5)

        self.listen_socket = s

        print("Now listening on ip: %s and port: %d" % (self.ip, self.port))

        while True:
            conn, addr = s.accept()
            data = conn.recv(BUFFER_SIZE)
            message = m.decode_message(data)
            if message.type == mt.PREPARE:
                print("received PREPARE from id: %d" % (message.sender_id))
                self.startWorker(self.rcv_prepare, conn, message)
            elif message.type == mt.PROMISE:
                print("received PROMISE from id: %d" % (message.sender_id))
                self.startWorker(self.rcv_promise, conn, message)
            elif message.type == mt.ACCEPT:
                print("received ACCEPT from id: %d" % (message.sender_id))
                self.startWorker(self.rcv_accept, conn, message)
            elif message.type == mt.ACCEPTED:
                print("received ACCEPTED from id: %d" % (message.sender_id))
                self.startWorker(self.rcv_acceptance, conn, message)
            elif message.type == mt.DECISION:
                print("received DECISION from id: %d" % (message.sender_id))
                self.startWorker(self.rcv_decision, conn, message)
            elif message.type == mt.NACK:
                print("received NACK from id: %d" % (message.sender_id))
                self.startWorker(self.rcv_nack, conn, message)


    def startWorker(self, target, conn, message):
        thread = Thread(target=target, args=(conn, message, ))
        tname = thread.getName()
        thread.daemon = True
        thread.start()


    """
    Acceptor Logic
    """

    def rcv_prepare(self, conn, message):
        if message.round <= self.latest_round:
            nack = m.Message(mt.NACK, target_id=message.sender_id)
            self.send_message(conn, nack)
            return

        if message.depth <= self.blockchain.depth:
            nack = m.Message(mt.NACK, target_id=message.sender_id)
            self.send_message(conn, nack)
            return

        if self.accepted_block:
            # send promise with block
            promise = m.Message(mt.PROMISE, target_id=message.sender_id)
            self.send_message(conn, promise)
            return

        self.latest_round = message.round

        # send promise w/o value
        promise = m.Message(mt.PROMISE, target_id=message.sender_id)
        self.send_message(conn, promise)


    def rcv_promise(self, conn, message):
        self.promises+=1 # member variable?
        if self.promises >= MAJORITY:
            # broadcast accept
            self.proposer_phase = pp.ACCEPT
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
        conn.close()
        accepted = m.Message(mt.ACCEPTED)
        self.broadcast_message(accepted)


    def rcv_acceptance(self, conn, message):
        if message.proposer_id == self.id:
            self.acceptances += 1
            if self.acceptances >= MAJORITY:
                self.proposer_phase = pp.DECISION
                # TODO: implement buffer queue for transactions entered after proposer phase begins
                self.updateFromBlock(self.proposed_block, self.proposed_depth)

                decision = m.Message(mt.DECISION,
                                     proposer_id=self.id,
                                     depth=self.proposed_depth,
                                     round=self.proposed_round,
                                     block=self.proposed_block
                                     )

                conn.close()
                self.broadcast_message(decision)
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
        conn.close()


    def rcv_nack(self, conn, message):
        print("nack received")
        conn.close()

    """
    Proposer Logic
    """

    def send_prepare(self):
        print("Sending PREPARE")
        self.proposed_round = self.latest_round + 1
        self.proposed_depth = self.blockchain.depth + 1
        self.proposed_block = self.queue_to_list(self.queue)

        self.proposer_phase = pp.PREPARE

        prepare = m.Message(mt.PREPARE,
                            proposer_id=self.id,
                            round=self.proposed_round,
                            depth=self.proposed_depth,
                            block=self.proposed_block)
        self.broadcast_message(prepare)


    def proposer_loop(self):
        while (self.queue_state == qs.NONEMPTY):
            if (self.proposer_phase == pp.NONE):
                self.send_prepare()
            time.sleep(self.propose_cooldown)
        return

    def start_proposer_loop_thread(self):
        thread = Thread(target=self.proposer_loop, args=())
        tname = thread.getName()
        thread.daemon = True
        thread.start()


    """
    Utility Methods
    """

    def send_message(self, conn, message):
        message.sender_id = self.id
        print("\nAttempting message send from %d to %d" % (message.sender_id, message.target_id))
        print("\n",conn.getsockname())
        print("\n",conn.getpeername(),"\n")
        message = m.encode_message(message)
        conn.send(message)
        conn.close()

    def broadcast_message(self, message):
        # for i in range(len(ip_addrs)):
        for i in range(NUM_NODES):
            if not i == self.id:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((ip_addrs[i], ports[i]))
                message.target_id = i
                self.send_message(sock, message)
        print("Broadcast complete")

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
        self.queue_state = qs.EMPTY

    def reset_acceptor_state(self):
        self.accepted_block = None

    def queue_to_list(self, queue):
        l = []
        while queue.qsize() > 0:
            l.append(queue.get())
        return l


n = Node(int(sys.argv[1]))