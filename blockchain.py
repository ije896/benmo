
class Blockchain:
    def __init__(self):
        self.blocks = []
        self.depth = 0

    def addBlock(self, block):
        pass

class Block:
    def __init__(self):
        self.transactions = []

    def addTransaction(self, transaction):
        self.transactions.append(transaction)
        pass

class Transaction:
    def __init__(self, amount, debit_node, credit_node):
        self.amount = amount
        self.debit_node = debit_node
        self.credit_node = credit_node
