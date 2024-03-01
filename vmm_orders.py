import smartpy as sp  # type: ignore
import utilities.Address as Address
from vmm_contract_types import vmm_types


@sp.module
def orders():
    class VmmOrders(sp.Contract):
        def __init__(self, metadata, administrator, fund_manager):
            # Metadata of the contract
            self.data.metadata = sp.cast(metadata, sp.big_map[sp.string, sp.bytes])
            # Administration panel to handle the contract
            self.data.administration_panel = sp.cast(
                sp.record(
                    administrator=administrator,
                    pendingAdministrator=None,
                    positionManagers={administrator},
                    fundManager=fund_manager,
                ),
                vmm_types.administration_panel_type,
            )
            # Orders Bigmap
            self.data.orders = sp.cast(
                sp.big_map(), sp.big_map[sp.int, vmm_types.create_order_type]
            )
            # Last order id
            self.data.last_order_id = sp.int(0)
            # Decimal precision of contract
            self.data.decimal = sp.cast(6, sp.int)
            # Decimal amount of contract
            self.data.decimal_amount = sp.cast(1_000_000, sp.int)
            # Status of the contract (0: notInitialized, 1: active, 2: closeOnly, 3: paused)
            self.data.status = sp.cast(0, sp.int)

        @sp.entrypoint
        def createOrder(self, params):
            sp.cast(params, vmm_types.create_order_type)
            assert self.data.status == 1, "Contract is not active"
            self.data.orders[self.data.last_order_id] = params
            self.data.last_order_id += 1

        @sp.entrypoint
        def updateOrder(self, order_id, params):
            sp.cast(params, vmm_types.create_order_type)
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            self.data.orders[order_id] = params

        @sp.entrypoint
        def cancelOrder(self, order_id):
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            del self.data.orders[order_id]

        @sp.entrypoint
        def executeOrder(self, order_id):
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            # TODO: Execute order code
            self.data.orders[order_id].order_status = 1


if __name__ == "__main__":

    @sp.add_test()
    def test():
        sc = sp.test_scenario("vmm_orders", [vmm_types, sp.utils, orders])
        sc.h1("VMM Orders Contract")

        sc.h2("Originate Orders Contract")
        vmm_orders = orders.VmmOrders(
            metadata=sp.scenario_utils.metadata_of_url("https://example.com"),
            administrator=Address.admin,
            fund_manager=Address.elon,
        )
        sc += vmm_orders
