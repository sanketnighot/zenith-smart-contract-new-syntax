import smartpy as sp  # type: ignore
from USDt import usdt
from vmm_contract import vmm
from vmm_orders import orders
import utilities.Address as Address
from utilities.FA2 import fa2
from utilities.Helpers import helpers
from Oracle import oracle
from vmm_contract_types import vmm_types


if __name__ == "__main__":

    @sp.add_test()
    def test():
        sc = sp.test_scenario(
            "vmm_test", [vmm_types, sp.utils, oracle, fa2, usdt, helpers, vmm, orders]
        )
        sc.h1("VMM Contract")

        sc.h2("Originate USDt Contract")
        usdt_token = usdt.USDt(
            administrator=Address.admin,
            metadata=sp.scenario_utils.metadata_of_url("https://example.com"),
        )
        sc += usdt_token

        sc.h2("Originate Oracle Contract")
        oracle_contract = oracle.Oracle()
        sc += oracle_contract
        oracle_contract.updatePrice(8000000, _now=sp.timestamp(12))

        sc.h2("Originate VMM Contract")
        vmm_contract = vmm.VMM(
            metadata=sp.scenario_utils.metadata_of_url("https://example.com"),
            administrator=Address.alice,
            usd_contract_address=usdt_token.address,
            oracle_address=oracle_contract.address,
            fund_manager=Address.elon,
        )
        sc += vmm_contract

        sc.h2("Originate Orders Contract")
        vmm_orders = orders.VmmOrders(
            metadata=sp.scenario_utils.metadata_of_url("https://example.com"),
            administrator=Address.admin,
            fund_manager=Address.elon,
        )
        sc += vmm_orders

        sc.h2("Testing Propose Admin")
        vmm_contract.proposeAdmin(Address.admin, _sender=Address.alice)
        vmm_contract.updateAdmin(_sender=Address.bob, _valid=False)
        vmm_contract.updateAdmin(_sender=Address.admin)

        sc.h2("Testing Set VMM")
        vmm_contract.setVmm(12500000000, _sender=Address.admin)

        sc.h2("Testing Set Position Manager")
        vmm_contract.addPositionManager(vmm_orders.address, _sender=Address.admin)

        usdt_token.mint(
            sp.record(
                amount=sp.nat(1000000000000),
                to_=Address.admin,
                token=sp.variant("new", {"0": sp.bytes("0x746f6b656e30")}),
            ),
            _sender=Address.admin,
        )
        usdt_token.mint(
            sp.record(
                amount=sp.nat(1000000000000),
                to_=Address.alice,
                token=sp.variant("existing", sp.nat(0)),
            ),
            _sender=Address.admin,
        )
        usdt_token.mint(
            sp.record(
                amount=sp.nat(1000000000000),
                to_=Address.bob,
                token=sp.variant("existing", sp.nat(0)),
            ),
            _sender=Address.admin,
        )

        usdt_token.update_operators(
            [
                sp.variant(
                    "add_operator",
                    sp.record(
                        owner=Address.alice, operator=vmm_contract.address, token_id=0
                    ),
                )
            ],
            _sender=Address.alice,
        )
        usdt_token.update_operators(
            [
                sp.variant(
                    "add_operator",
                    sp.record(
                        owner=Address.bob, operator=vmm_contract.address, token_id=0
                    ),
                )
            ],
            _sender=Address.bob,
        )
        usdt_token.update_operators(
            [
                sp.variant(
                    "add_operator",
                    sp.record(
                        owner=Address.admin, operator=vmm_contract.address, token_id=0
                    ),
                )
            ],
            _sender=Address.admin,
        )

        # oracle_contract.updatePrice(1000000).run(now=sp.timestamp(12))

        sc.h2("Testing Increase Position")
        vmm_contract.increasePosition(
            sp.record(
                position_holder=Address.alice,
                direction=sp.int(1),
                usd_amount=sp.int(2000000000),
                leverage_multiple=sp.int(2),
            ),
            _sender=Address.alice,
        )

        vmm_contract.increasePosition(
            sp.record(
                position_holder=Address.bob,
                direction=sp.int(2),
                usd_amount=sp.int(2000000000),
                leverage_multiple=sp.int(3),
            ),
            _sender=Address.bob,
            _valid=False,
        )

        oracle_contract.updatePrice(8000000, _now=sp.timestamp(3618))

        sc.h2("Testing Distribute Funding")
        vmm_contract.distributeFunding(_sender=Address.alice, _now=sp.timestamp(3620))

        sc.h2("Testing Close Position")
        vmm_contract.closePosition(Address.alice, _sender=Address.alice)
        vmm_contract.closePosition(Address.bob, _sender=Address.bob, _valid=False)

        sc.show(vmm_contract.data)
        sc.show(usdt_token.data.ledger)

        # Create Order
        sc.h2("Testing Create Order")
        vmm_orders.createOrder(
            sp.record(
                position_holder=Address.alice,
                vmm_address=vmm_contract.address,
                order_type=sp.int(0),
                trigger_price=sp.int(0),
                limit_price=sp.int(0),
                amount_in=sp.int(2000000000),
                leverage_multiple=sp.int(2),
                direction=sp.int(1),
                stop_trigger_price=None,
                stop_limit_price=None,
                take_trigger_price=None,
                take_limit_price=None,
                expiration=sp.int(0),
                order_status=sp.int(0),
            ),
            _sender=Address.alice,
        )

        sc.show(vmm_contract.data)
        sc.show(usdt_token.data.ledger)

        # Close Order
        sc.h2("Testing Close Order")
        vmm_orders.executeCloseOrder(0, _sender=Address.alice)
        vmm_orders.executeCloseOrder(0, _sender=Address.alice, _valid=False)

        sc.show(vmm_contract.data)
        sc.show(usdt_token.data.ledger)
