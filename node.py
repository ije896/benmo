# Node class
import queue as q
from blockchain import *
import message as m
import time, socket, os, sys
from threading import Thread
from message import MessageType as mt
from enum import IntEnum
import random
import copy

from config import *


# TODO: is majority a const, 3, or is it dynamic as nodes go on/offline
# TODO: if dynamic, do we let the other nodes know when one goes offline/alert for changes in cluster size?
MAJORITY = 3
NUM_NODES = 5

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
        self.balance_after_queue = 100

        self.ip = ip_addrs[id]
        self.port = ports[id]

        self.latest_round = 0

        # state for acceptor phase -- resets after a decision is received
        self.accepted_block = None
        self.acceptor_phase = ap.NONE

        # state for proposer phase -- resets after decision is sent
        self.promises = 1
        self.acceptances = 1
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
            action = input('Enter a command (s/p/sc): ').lower().strip()
            if action=='s':
                amount = int(input('Enter an amount: ').lower().strip())
                credit_node = ""
                while (credit_node == ""):
                    credit_node = int(input('Enter destination for transaction(1-5): ').lower().strip())
                    if (credit_node not in range(NUM_NODES)):
                        print("Destination not valid.")
                        credit_node = ""
                self.moneyTransfer(amount, credit_node)
            if action=='p':
                self.print_all()
            if action=='sc':
                self.listen_socket.close()
                exit(0)


    def moneyTransfer(self, amount, credit_node):
        if credit_node == self.id:
            print("Can't send money to self")
            return

        if self.balance_after_queue>=amount:
            self.balance_after_queue -= amount

            trans = Transaction(amount, self.id, credit_node)
            self.queue.put(trans)

            if self.queue.qsize() == 1:
                self.queue_state = qs.NONEMPTY
                self.start_proposer_loop_thread()
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
        print("\nState of node %d : pp: %d, qp: %d" % (self.id, self.proposer_phase, self.queue_state))

    def print_blockchain(self):
        print("Node blockchain: %s" % self.blockchain.print_str())

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
                print("received PREPARE from id: %d, prop round: %d, prop depth: %d, prop block length: %d" %
                      (message.sender_id, message.round, message.depth, len(message.block)))
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
            elif message.type == mt.NACK or message.type == mt.ROUND_NACK or message.type == mt.DEPTH_NACK:
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
        target_id = message.sender_id
        if message.round <= self.latest_round:
            nack = m.Message(mt.ROUND_NACK,
                             target_id=message.sender_id,
                             round=self.latest_round,
                             comment="prepare nack, round is too low")
            # self.send_message(conn, nack)
            self.send_message_to_id(target_id, nack)
            return

        if message.depth <= self.blockchain.depth:
            nack = m.Message(mt.DEPTH_NACK,
                             target_id=message.sender_id,
                             depth=self.blockchain.depth,
                             blockchain=self.blockchain,
                             comment="prepare nack, depth is too low")
            # self.send_message(conn, nack)
            self.send_message_to_id(target_id, nack)
            return

        if self.accepted_block:
            # TODO: send promise with block
            promise = m.Message(mt.PROMISE,
                                blockchain=self.blockchain,
                                target_id=message.sender_id)
            # self.send_message(conn, promise)
            self.send_message_to_id(target_id, promise)
            return

        self.latest_round = message.round

        # send promise w/o value
        promise = m.Message(mt.PROMISE, target_id=message.sender_id)
        # self.send_message(conn, promise)
        self.send_message_to_id(target_id, promise)


    def rcv_promise(self, conn, message):
        # TODO: If value is appended to promise...
        if self.proposer_phase == pp.PREPARE:
            self.promises+=1 # member variable?
            if self.promises >= MAJORITY:
                # broadcast accept
                self.proposer_phase = pp.ACCEPT
                conn.close()
                accept = m.Message(mt.ACCEPT,
                                sender_id=self.id,
                                 proposer_id=self.id,
                                 depth=self.proposed_depth,
                                 round=self.proposed_round,
                                 block=self.proposed_block)
                self.broadcast_message(accept)


    def rcv_accept(self, conn, message):
        target_id = message.sender_id
        if message.round < self.latest_round:
            nack = m.Message(mt.ROUND_NACK,
                             round=self.latest_round,
                             comment="accept nack, round is too low")
            # self.send_message(conn, nack)
            self.send_message_to_id(target_id, nack)
            return

        if message.depth <= self.blockchain.depth:
            nack = m.Message(mt.DEPTH_NACK,
                             target_id=message.sender_id,
                             depth=self.blockchain.depth,
                             blockchain=self.blockchain,
                             comment="prepare nack, depth is too low")
            # self.send_message(conn, nack)
            self.send_message_to_id(target_id, nack)
            return

        self.accepted_block = message.block
        # broadcast accepted
        conn.close()
        accepted = m.Message(mt.ACCEPTED,
                             sender_id=self.id,
                             proposer_id=message.proposer_id,
                             depth=message.depth,
                             round=message.round,
                             block=message.block
                             )
        self.broadcast_message(accepted)


    def rcv_acceptance(self, conn, message):
        if message.proposer_id == self.id and self.proposer_phase == pp.ACCEPT:
            self.acceptances += 1
            if self.acceptances >= MAJORITY:
                print("\nMajority Acceptance; executing decision")
                self.proposer_phase = pp.DECISION
                # TODO: implement buffer queue for transactions entered after proposer phase begins
                self.updateFromBlock(self.proposed_block, self.proposed_depth)

                decision = m.Message(mt.DECISION,
                                     sender_id=self.id,
                                     proposer_id=self.id,
                                     depth=self.proposed_depth,
                                     round=self.proposed_round,
                                     block=self.proposed_block
                                     )

                conn.close()
                self.broadcast_message(decision)
                self.reset_proposer_state()
                self.print_all()



    def rcv_decision(self, conn, message):
        target_id = message.sender_id
        if message.round < self.latest_round:
            nack = m.Message(mt.NACK, comment="decision nack, round is too low")
            # self.send_message(conn, nack)
            self.send_message_to_id(target_id, nack)
            return
        if message.depth <= self.blockchain.depth:
            nack = m.Message(mt.NACK, comment="decision nack, depth is too low")
            # self.send_message(conn, nack)
            self.send_message_to_id(target_id, nack)
            return
        self.updateFromBlock(message.block, message.depth)
        self.reset_acceptor_state()
        conn.close()


    def rcv_nack(self, conn, message):
        # TODO: Handle double nack case where it would bump up round number twice
        print("\nnack received: %s" % message.comment)
        conn.close()

        if (message.type == mt.DEPTH_NACK):
            self.blockchain = message.blockchain
        elif (message.type == mt.ROUND_NACK):
            self.latest_round = message.round

        if (not self.proposer_phase == pp.NONE):
            self.proposer_phase = pp.NONE

    """
    Proposer Logic
    """

    def send_prepare(self):
        # self.latest_round += 1
        self.proposed_round = self.latest_round + 1
        self.proposed_depth = self.blockchain.depth + 1
        # print(self.proposed_block)
        self.proposed_block = self.queue_to_list(self.queue)
        # print(self.proposed_block)

        self.proposer_phase = pp.PREPARE

        print("\nSending PREPARE, round: %d, depth: %d, length of block: %d" % (self.proposed_round, self.proposed_depth, len(self.proposed_block)))

        prepare = m.Message(mt.PREPARE,
                            sender_id=self.id,
                            proposer_id=self.id,
                            round=self.proposed_round,
                            depth=self.proposed_depth,
                            block=self.proposed_block)
        self.broadcast_message(prepare)


    def proposer_loop(self):
        while (True):
            time.sleep(self.propose_cooldown)
            if (self.queue_state == qs.NONEMPTY):
                print("\nRestarted proposer loop, id: %d, pphase: %d" % (self.id, self.proposer_phase))
                if (self.proposer_phase == pp.NONE):
                    self.send_prepare()
            else:
                print("\nEnding proposer loop")
                return

    def start_proposer_loop_thread(self):
        thread = Thread(target=self.proposer_loop, args=())
        tname = thread.getName()
        thread.daemon = True
        thread.start()


    """
    Utility Methods
    """

    def send_message_to_id(self, target_id, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip_addrs[target_id], ports[target_id]))
        message.target_id = target_id
        self.send_message(sock, message)

    def send_message(self, conn, message):
        time.sleep(random.random() * 1.5)
        message.sender_id = self.id
        # print("\nAttempting message send from %d to %d" % (message.sender_id, message.target_id))
        # print("\n",conn.getsockname())
        # print("\n",conn.getpeername(),"\n")
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
        # print("Broadcast complete")

    def updateFromBlock(self, block, depth):
        print("\nAttempting to update from block: ",block)
        print("\nAt depth: %d" % depth)
        self.blockchain.addBlock(block)
        for trans in self.blockchain.blocks[depth]:
            if trans.credit_node == self.id:
                self.balance+=trans.amount
                self.balance_after_queue += trans.amount
            if trans.debit_node == self.id:
                self.balance-=trans.amount


    def reset_proposer_state(self):
        self.acceptances = 1
        self.promises = 1
        self.proposed_block = None
        self.queue = q.Queue()
        self.queue_state = qs.EMPTY
        self.proposer_phase = pp.NONE

    def reset_acceptor_state(self):
        self.accepted_block = None

    def queue_to_list(self, queue):
        temp_q = q.Queue()
        temp_q.queue = copy.deepcopy(queue.queue)
        l = []
        while temp_q.qsize() > 0:
            l.append(temp_q.get())
        return l


n = Node(int(sys.argv[1]))