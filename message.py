import pickle
from enum import IntEnum

class MessageType(IntEnum):
    PREPARE = 0
    PROMISE = 1
    ACCEPT = 2
    ACCEPTED = 3
    DECISION = 4
    # NACK = 6
    # REQ_BLOCKCHAIN = 7

class Message:
    def __init__(self, type, log, time_table, votes):
        self.type = type
        self.log = log
        self.time_table = time_table
        self.votes = votes

def generate_request(action, type, quantity, kiosk_id):
    return {"action": action,
            "type": type,
            "quantity": quantity,
            "kiosk_id": kiosk_id,
            }

def generate_response(status):
    return {"status": status}

def encode_message(message):
    return pickle.dumps(message)

def decode_message(message):
    return pickle.loads(message)
