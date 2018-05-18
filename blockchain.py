
class Blockchain:
    def __init__(self):
        self.blocks = []


class Block:
    def __init__(self):
        self.transactions = []

class Transaction:
    def __init__(self, amount, debit_node, credit_node):
        self.amount = amount
        self.debit_node = debit_node
        self.credit_node = credit_node
