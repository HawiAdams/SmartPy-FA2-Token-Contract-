from smartpy import sp

# FA2 Token Implementation
class FA2Token(sp.io.Contract):
    def __init__(self, admin):
        self.init(
            admin=admin,
            ledger=sp.io.big_map(tvalue=sp.TNat),
            operators=sp.io.big_map(tkey=sp.TAddress, tvalue=sp.TNat)
        )

    @sp.io.entry_point
    def transfer(self, params):
        sp.set_type(params, sp.TRecord(from_=sp.TAddress, txs=sp.TList(sp.TRecord(to_=sp.TAddress, token_id=sp.TNat, amount=sp.TNat))))

        sp.verify(sp.sender == self.data.admin, message="Not an admin")
        for tx in params.txs:
            from_balance = sp.local("from_balance", self.data.ledger[tx.from_][tx.token_id])
            to_balance = sp.local("to_balance", sp.local("ledger", self.data.ledger[tx.to_]).get(tx.token_id, 0))

            sp.verify(from_balance.value >= tx.amount, message="Not enough balance")
            sp.verify(self.data.operators.get(tx.from_, 0) & 1 == 1, message="Not an operator")

            self.data.ledger[tx.from_][tx.token_id] = from_balance.value - tx.amount
            self.data.ledger[tx.to_][tx.token_id] = to_balance + tx.amount

    @sp.io.entry_point
    def update_operators(self, params):
        sp.set_type(params, sp.TList(sp.TRecord(
            add_operator=sp.TRecord(operator=sp.TAddress, token_id=sp.TNat),
            remove_operator=sp.TRecord(operator=sp.TAddress, token_id=sp.TNat)
        )))

        for op in params:
            if op.add_operator is not None:
                self.data.operators[op.add_operator.operator][op.add_operator.token_id] = 1
            if op.remove_operator is not None:
                sp.verify(sp.sender == self.data.admin or sp.sender == op.remove_operator.operator,
                          message="Not authorized to remove operator")
                sp.verify(self.data.operators[op.remove_operator.operator].get(op.remove_operator.token_id, 0) & 1 == 1,
                          message="Operator not found")
                del self.data.operators[op.remove_operator.operator][op.remove_operator.token_id]

# Test scenario
@sp.io.add_test(name="FA2Token")
def test():
    # Define test accounts
    admin = sp.io.test_account("admin")
    alice = sp.io.test_account("alice")
    bob = sp.io.test_account("bob")

    # Initialize the contract
    token = FA2Token(admin.address)
    scenario = sp.io.test_scenario()
    scenario += token

    # Mint some tokens
    token.update_operators([sp.io.record(add_operator=sp.io.record(operator=admin.address, token_id=0))])
    token.transfer([sp.io.record(from_=admin.address, txs=[sp.io.record(to_=alice.address, token_id=0, amount=100)])])

    # Attempt to transfer from alice to bob (should fail as alice is not an operator)
    token.transfer([sp.io.record(from_=alice.address, txs=[sp.io.record(to_=bob.address, token_id=0, amount=10)])], valid=False)

    # Make alice an operator
    token.update_operators([sp.io.record(add_operator=sp.io.record(operator=alice.address, token_id=0))])

    # Now alice can transfer to bob
    token.transfer([sp.io.record(from_=alice.address, txs=[sp.io.record(to_=bob.address, token_id=0, amount=10)])])

    # Check balances after transfers
    scenario.h3("Balances after transfers")
    scenario += token.data.ledger
