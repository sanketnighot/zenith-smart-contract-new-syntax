import sys

sys.path.insert(0, "/Users/sanket/Zenith/Projects/Testnet/zenith-smart-contracts")
import smartpy as sp  # type: ignore
from utilities.FA2 import fa2
import utilities.Address as Address

# main = FA2.main


@sp.module
def usdt():
    class USDt(fa2.Fa2FungibleMinimal):
        def __init__(self, administrator, metadata):
            fa2.Fa2FungibleMinimal.__init__(self, administrator, metadata)


if __name__ == "__main__":

    @sp.add_test("USDt")
    def test():
        sc = sp.test_scenario([fa2, usdt])

        sc.h1("USDt Contract")
        usdt_token = usdt.USDt(
            administrator=Address.admin,
            metadata=sp.utils.metadata_of_url("https://example.com"),
        )
        sc += usdt_token
