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

        # Call Get Mark and Index Price from VMM Contract View
        @sp.private(with_operations=True)
        def callGetIndexAndMarkPriceView(self, vmm_address):
            sp.cast(vmm_address, sp.address)
            view_data = sp.view(
                "getIndexAndMarkPrice",
                vmm_address,
                (),
                sp.record(index_price=sp.int, mark_price=sp.int),
            ).unwrap_some()
            return view_data

        # Call Get Position Data from VMM Contract View
        @sp.private(with_operations=True)
        def callGetPositionDataView(self, vmm_address, position_holder):
            sp.cast(vmm_address, sp.address)
            sp.cast(position_holder, sp.address)
            view_data = sp.view(
                "getPositionData",
                vmm_address,
                position_holder,
                vmm_types.positions_value,
            ).unwrap_some()
            return view_data

        # Call Increase Position from VMM Contract
        @sp.private(with_operations=True)
        def callIncreasePosition(self, params):
            sp.cast(
                params,
                sp.record(
                    vmm_address=sp.address,
                    position_holder=sp.address,
                    direction=sp.int,
                    usd_amount=sp.int,
                    leverage_multiple=sp.int,
                ),
            )
            contractParams = sp.contract(
                sp.record(
                    position_holder=sp.address,
                    direction=sp.int,
                    usd_amount=sp.int,
                    leverage_multiple=sp.int,
                ),
                params.vmm_address,
                "increasePosition",
            ).unwrap_some()

            dataToBeSent = sp.record(
                position_holder=params.position_holder,
                direction=params.direction,
                usd_amount=params.usd_amount,
                leverage_multiple=params.leverage_multiple,
            )

            sp.transfer(dataToBeSent, sp.mutez(0), contractParams)

        # Call Close Position from VMM Contract
        @sp.private(with_operations=True)
        def callClosePosition(self, params):
            sp.cast(
                params, sp.record(position_holder=sp.address, vmm_address=sp.address)
            )
            contractParams = sp.contract(
                sp.address, params.vmm_address, "closePosition"
            ).unwrap_some()
            sp.transfer(params.position_holder, sp.mutez(0), contractParams)

        #  Call Decrease Position from VMM Contract
        @sp.private(with_operations=True)
        def callDecreasePosition(self, params):
            sp.cast(
                params,
                sp.record(
                    vmm_address=sp.address,
                    position_holder=sp.address,
                    direction=sp.int,
                    usd_amount=sp.int,
                ),
            )
            contractParams = sp.contract(
                sp.record(
                    position_holder=sp.address,
                    direction=sp.int,
                    usd_amount=sp.int,
                ),
                params.vmm_address,
                "decreasePosition",
            ).unwrap_some()

            dataToBeSent = sp.record(
                position_holder=params.position_holder,
                direction=params.direction,
                usd_amount=params.usd_amount,
            )

            sp.transfer(dataToBeSent, sp.mutez(0), contractParams)

        #  Call Add Margin from VMM Contract
        @sp.private(with_operations=True)
        def callAddMargin(self, params):
            sp.cast(
                params,
                sp.record(
                    vmm_address=sp.address,
                    position_holder=sp.address,
                    amount=sp.int,
                ),
            )
            contractParams = sp.contract(
                sp.record(position_holder=sp.address, amount=sp.int),
                params.vmm_address,
                "addMargin",
            ).unwrap_some()

            dataToBeSent = sp.record(
                position_holder=params.position_holder,
                amount=params.amount,
            )

            sp.transfer(dataToBeSent, sp.mutez(0), contractParams)

        #  Call Remove Margin from VMM Contract
        @sp.private(with_operations=True)
        def callRemoveMargin(self, params):
            sp.cast(
                params,
                sp.record(
                    vmm_address=sp.address,
                    position_holder=sp.address,
                    amount=sp.int,
                ),
            )
            contractParams = sp.contract(
                sp.record(position_holder=sp.address, amount=sp.int),
                params.vmm_address,
                "removeMargin",
            ).unwrap_some()

            dataToBeSent = sp.record(
                position_holder=params.position_holder,
                amount=params.amount,
            )

            sp.transfer(dataToBeSent, sp.mutez(0), contractParams)

        #  Call Take Profit from VMM Contract
        @sp.private(with_operations=True)
        def callTakeProfit(self, params):
            sp.cast(
                params,
                sp.record(
                    vmm_address=sp.address,
                    position_holder=sp.address,
                ),
            )
            contractParams = sp.contract(
                sp.address, params.vmm_address, "takeProfit"
            ).unwrap_some()
            sp.transfer(params.position_holder, sp.mutez(0), contractParams)

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
            assert params.position_holder == sp.sender, "InvalidPositionHolder"
            self.data.orders[self.data.last_order_id] = params
            if (params.order_type == 0) and (params.trigger_price == 0):
                order_params = sp.record(
                    vmm_address=params.vmm_address,
                    position_holder=params.position_holder,
                    direction=params.direction,
                    usd_amount=params.amount_in,
                    leverage_multiple=params.leverage_multiple,
                )
                self.callIncreasePosition(order_params)
                self.data.orders[self.data.last_order_id].order_status = 1
            self.data.last_order_id += 1

        # Update Order
        @sp.entrypoint
        def updateOrder(self, order_id, params):
            sp.cast(params, vmm_types.create_order_type)
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            self.data.orders[order_id] = params

        # Cancel Order
        @sp.entrypoint
        def cancelOrder(self, order_id):
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            del self.data.orders[order_id]

        # Execute Limit Order
        @sp.entrypoint
        def executeLimitOrder(self, order_id):
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            # TODO: Check the Trigger Price and Current Mark Price are in range of execution
            current_index_and_mark_price = self.callGetIndexAndMarkPriceView(
                self.data.orders[order_id].vmm_address
            )
            if (self.data.orders[order_id].direction == 1) and (
                current_index_and_mark_price.mark_price
                <= self.data.orders[order_id].trigger_price
            ):
                order_params = sp.record(
                    vmm_address=self.data.orders[order_id].vmm_address,
                    position_holder=self.data.orders[order_id].position_holder,
                    direction=self.data.orders[order_id].direction,
                    usd_amount=self.data.orders[order_id].amount_in,
                    leverage_multiple=self.data.orders[order_id].leverage_multiple,
                )
                self.callIncreasePosition(order_params)
                self.data.orders[order_id].order_status = 1
            if (self.data.orders[order_id].direction == 2) and (
                current_index_and_mark_price.mark_price
                >= self.data.orders[order_id].trigger_price
            ):
                order_params = sp.record(
                    vmm_address=self.data.orders[order_id].vmm_address,
                    position_holder=self.data.orders[order_id].position_holder,
                    direction=self.data.orders[order_id].direction,
                    usd_amount=self.data.orders[order_id].amount_in,
                    leverage_multiple=self.data.orders[order_id].leverage_multiple,
                )
                self.callIncreasePosition(order_params)
                self.data.orders[order_id].order_status = 1

        # Execute Close Position
        @sp.entrypoint
        def executeCloseOrder(self, order_id):
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            assert (
                sp.sender == self.data.orders[order_id].position_holder
            ), "NotAuthorized"
            assert self.data.orders[order_id].order_status == 1, "Order is not active"
            order_params = sp.record(
                vmm_address=self.data.orders[order_id].vmm_address,
                position_holder=self.data.orders[order_id].position_holder,
            )
            self.callClosePosition(order_params)
            self.data.orders[order_id].order_status = 2

        # Trigger Stop Loss
        @sp.entrypoint
        def triggerStopLoss(self, order_id):
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            current_index_and_mark_price = self.callGetIndexAndMarkPriceView(
                self.data.orders[order_id].vmm_address
            )
            if (self.data.orders[order_id].direction == 1) and (
                current_index_and_mark_price.mark_price
                <= self.data.orders[order_id].stop_trigger_price.unwrap_some()
            ):
                order_params = sp.record(
                    vmm_address=self.data.orders[order_id].vmm_address,
                    position_holder=self.data.orders[order_id].position_holder,
                )
                self.callClosePosition(order_params)
                self.data.orders[order_id].order_status = 2
            if (self.data.orders[order_id].direction == 2) and (
                current_index_and_mark_price.mark_price
                >= self.data.orders[order_id].stop_trigger_price.unwrap_some()
            ):
                order_params = sp.record(
                    vmm_address=self.data.orders[order_id].vmm_address,
                    position_holder=self.data.orders[order_id].position_holder,
                )
                self.callClosePosition(order_params)
                self.data.orders[order_id].order_status = 2

        # Trigger Take Profit
        @sp.entrypoint
        def triggerTakeProfit(self, order_id):
            assert self.data.status == 1, "Contract is not active"
            assert self.data.orders.contains(order_id), "Order does not exist"
            current_index_and_mark_price = self.callGetIndexAndMarkPriceView(
                self.data.orders[order_id].vmm_address
            )
            if (self.data.orders[order_id].direction == 1) and (
                current_index_and_mark_price.mark_price
                >= self.data.orders[order_id].take_trigger_price.unwrap_some()
            ):
                order_params = sp.record(
                    vmm_address=self.data.orders[order_id].vmm_address,
                    position_holder=self.data.orders[order_id].position_holder,
                )
                self.callTakeProfit(order_params)
                self.data.orders[order_id].order_status = 2
