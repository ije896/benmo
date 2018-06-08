import pickle
from enum import IntEnum

class MessageType(IntEnum):
    PREPARE = 0
    PROMISE = 1
    ACCEPT = 2
    ACCEPTED = 3
    DECISION = 4
    NACK = 6
    DEPTH_NACK = 7
    ROUND_NACK = 8
    # REQ_BLOCKCHAIN = 7

class Message:
    def __init__(self, type, ip=None, port=None, round=None, depth=None, block=None, proposer_id=None, sender_id=None, target_id=None, comment=None, blockchain=None):
        self.type = type
        self.ip = ip
        self.port = port
        self.round = round
        self.depth = depth
        self.block = block
        self.proposer_id = proposer_id
        self.sender_id = sender_id
        self.target_id = target_id
        self.comment = comment
        self.blockchain = blockchain

def encode_message(message):
    return pickle.dumps(message)

def decode_message(message):
    return pickle.loads(message)
