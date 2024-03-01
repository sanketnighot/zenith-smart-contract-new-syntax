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
            self.data.status = sp.cast(1, sp.int)

        @sp.private(with_storage="read-only")
        def _isAdmin(self):
            assert sp.sender == self.data.administration_panel.administrator, "NotAdmin"

        @sp.private(with_storage="read-only")
        def _isPositionManager(self):
            assert self.data.administration_panel.positionManagers.contains(
                sp.sender
            ), "NotPositionManager"

        @sp.private(with_storage="read-only")
        def _checkStatus(self, statusCode):
            sp.cast(statusCode, sp.int)
            assert self.data.status == statusCode, "InvalidStatus"

        # Update Admin
        @sp.entrypoint
        def proposeAdmin(self, newAdminAddress):
            sp.cast(newAdminAddress, sp.address)
            self._isAdmin()
            self.data.administration_panel.pendingAdministrator = sp.Some(
                newAdminAddress
            )

        # Verify Admin
        @sp.entrypoint
        def updateAdmin(self):
            assert (
                self.data.administration_panel.pendingAdministrator.is_some()
            ), "NoPendingAdministrator"
            assert (
                sp.sender
                == self.data.administration_panel.pendingAdministrator.unwrap_some()
            ), "NotAuthorized"
            self.data.administration_panel.administrator = (
                self.data.administration_panel.pendingAdministrator.unwrap_some()
            )
            self.data.administration_panel.pendingAdministrator = None

        # Update Status
        @sp.entrypoint
        def update_status(self, new_status_code):
            self._isAdmin()
            sp.cast(new_status_code, sp.int)
            self.data.status = new_status_code

        # Add Position Manager
        @sp.entrypoint
        def add_position_manager(self, position_manager):
            sp.cast(position_manager, sp.address)
            self._isAdmin()
            self.data.administration_panel.positionManagers.add(position_manager)

        # Remove Position Manager
        @sp.entrypoint
        def remove_position_manager(self, position_manager):
            sp.cast(position_manager, sp.address)
            self._isAdmin()
            assert self.data.administration_panel.positionManagers.contains(
                position_manager
            ), "NotAPositionManager"
            self.data.administration_panel.positionManagers.remove(position_manager)

        # Update Decimal
        @sp.entrypoint
        def updateDecimal(self, decimal, decimal_amount):
            self._isAdmin()
            sp.cast(decimal, sp.int)
            self.data.decimal = decimal
            sp.cast(decimal_amount, sp.int)
            self.data.decimal_amount = decimal_amount

        # Create Order
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
