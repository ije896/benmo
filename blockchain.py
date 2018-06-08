
class Blockchain:
    def __init__(self):
        self.blocks = []
        self.depth = -1

    def addBlock(self, block):
        self.blocks.append(block)
        self.depth += 1

    def print(self):
        for i in range(len(self.blocks)):
            print("\nPrinting block %d" % i)
            for j in range(len(self.blocks[i])):
                print("\nTrans %d: %s" % (j, self.blocks[i][j].print_str()))


class Block:
    def __init__(self):
        self.transactions = []

    def addTransaction(self, transaction):
        self.transactions.append(transaction)

class Transaction:
    def __init__(self, amount, debit_node, credit_node):
        self.amount = amount
        self.debit_node = debit_node
        self.credit_node = credit_node

    def print(self):
        print("From %s to %s for amt: %d" % (self.debit_node, self.credit_node, self.amount))

    def print_str(self):
        return("From %s to %s for amt: %d" % (self.debit_node, self.credit_node, self.amount))
