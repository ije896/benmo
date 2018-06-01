import pickle
from enum import IntEnum

class MessageType(IntEnum):
    PREPARE = 0
    PROMISE = 1
    ACCEPT = 2
    ACCEPTED = 3
    DECISION = 4
    NACK = 6
    # REQ_BLOCKCHAIN = 7

class Message:
    def __init__(self, type, ip=None, port=None, round=None, depth=None, block=None, proposer_id=None):
        self.type = type
        self.ip = ip
        self.port = port
        self.round = round
        self.log = depth
        self.block = block
        self.proposer_id = proposer_id

def encode_message(message):
    return pickle.dumps(message)

def decode_message(message):
    return pickle.loads(message)
