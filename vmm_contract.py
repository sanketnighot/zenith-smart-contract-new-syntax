import smartpy as sp  # type: ignore
import utilities.Address as Address
from vmm_contract_types import vmm_types
from utilities.Helpers import helpers


@sp.module
def vmm():

    class VMM(helpers.Helpers):

        def __init__(
            self,
            metadata,
            administrator,
            fund_manager,
            usd_contract_address,
            oracle_address,
        ):
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
            # Decimal precision of contract
            self.data.decimal = sp.cast(6, sp.int)
            # Decimal amount of contract
            self.data.decimal_amount = sp.cast(1_000_000, sp.int)
            # Status of the contract (0: notInitialized, 1: active, 2: closeOnly, 3: paused)
            self.data.status = sp.cast(0, sp.int)
            # VMM State of the token pair
            self.data.vmm = sp.record(
                token_amount=sp.int(0), usd_amount=sp.int(0), invariant=sp.int(0)
            )
            # Active Positions
            self.data.positions = sp.cast(
                {}, sp.map[sp.address, vmm_types.positions_value]
            )
            # Funding Period of the contract
            self.data.funding_period = sp.cast(3600, sp.int)
            #  Previous Funding Time
            self.data.previous_funding_time = sp.cast(sp.now, sp.timestamp)
            # Upcoming Funding Time
            self.data.upcoming_funding_time = sp.cast(
                sp.add_seconds(sp.now, sp.int(3600)), sp.timestamp
            )
            self.data.transaction_fees = sp.cast(2, sp.int)
            helpers.Helpers.__init__(self, oracle_address, usd_contract_address)

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

        #  Update Fund Manager
        @sp.entrypoint
        def update_fund_manager(self, new_fund_manager):
            sp.cast(new_fund_manager, sp.address)
            self._isAdmin()
            self.data.administration_panel.fundManager = new_fund_manager

        @sp.entrypoint
        def updateOracleAddress(self, oracle_address):
            self._isAdmin()
            sp.cast(oracle_address, sp.address)
            self.updateIndexPrice()
            self.data.oracle_address = oracle_address
            sp.emit(
                sp.record(oracle_address=self.data.oracle_address),
                tag="ORACLE_ADDRESS_UPDATED",
            )

        @sp.entrypoint
        def updateFundingPeriod(self, funding_period):
            self._isAdmin()
            sp.cast(funding_period, sp.int)
            self.updateIndexPrice()
            self.data.funding_period = funding_period
            sp.emit(
                sp.record(funding_period=funding_period),
                tag="FUNDING_PERIOD_UPDATED",
            )

        @sp.entrypoint
        def setVmm(self, token_amount):
            self._isAdmin()

            sp.cast(token_amount, sp.int)
            assert self.data.vmm == sp.record(
                token_amount=sp.int(0), usd_amount=sp.int(0), invariant=sp.int(0)
            ), "VMM_ALREADY_SET"
            assert token_amount >= sp.int(0) * self.data.decimal, "INVALID_TOKEN_AMOUNT"
            self.updateIndexPrice()
            usd_amount = (
                token_amount * self.data.current_index_price
            ) / self.data.decimal
            self.data.vmm = sp.record(
                token_amount=token_amount,
                usd_amount=usd_amount,
                invariant=sp.mul(token_amount, usd_amount) / self.data.decimal,
            )

            self.data.current_mark_price = (
                self.data.vmm.usd_amount * self.data.decimal
            ) / self.data.vmm.token_amount
            self.data.previous_funding_time = sp.now
            self.data.upcoming_funding_time = sp.add_seconds(
                sp.now, self.data.funding_period
            )
            sp.emit(self.data.vmm, tag="VMM_CONFIGURED")

        @sp.entrypoint
        def distributeFunding(self):

            assert utils.seconds_of_timestamp(  # type: ignore
                self.data.upcoming_funding_time
            ) <= utils.seconds_of_timestamp(  # type: ignore
                sp.now
            ), "FUNDING_NOT_DUE"  # type: ignore
            self.updateIndexPrice()
            self.data.current_mark_price = (
                self.data.vmm.usd_amount * self.data.decimal
            ) / self.data.vmm.token_amount
            self.calculateFundingRate()
            price_difference = (
                self.data.current_mark_price - self.data.current_index_price
            )
            if price_difference < 0:
                if self.data.total_short > 0:
                    for y in self.data.positions.items():
                        if y.value.position == 2:
                            self.data.positions[
                                y.key
                            ].funding_amount = self.data.positions[
                                y.key
                            ].funding_amount - (
                                sp.mul(
                                    y.value.position_value,
                                    self.data.short_funding_rate.value,
                                )
                                / self.data.decimal
                            )
                            self.data.positions[y.key].collateral_amount = (
                                self.data.positions[y.key].collateral_amount
                                - (
                                    sp.mul(
                                        y.value.position_value,
                                        self.data.short_funding_rate.value,
                                    )
                                )
                                / self.data.decimal
                            )

                if self.data.total_long > 0:
                    for x in self.data.positions.items():
                        if x.value.position == 1:
                            self.data.positions[x.key].funding_amount += (
                                sp.mul(
                                    x.value.position_value,
                                    self.data.long_funding_rate.value,
                                )
                            ) / self.data.decimal
                            self.data.positions[x.key].collateral_amount += (
                                sp.mul(
                                    x.value.position_value,
                                    self.data.long_funding_rate.value,
                                )
                            ) / self.data.decimal
            if price_difference > 0:
                if self.data.total_long > 0:
                    for y in self.data.positions.items():
                        if y.value.position == 1:
                            self.data.positions[
                                y.key
                            ].funding_amount = self.data.positions[
                                y.key
                            ].funding_amount - (
                                (
                                    sp.mul(
                                        y.value.position_value,
                                        self.data.long_funding_rate.value,
                                    )
                                )
                                / self.data.decimal
                            )
                            self.data.positions[y.key].collateral_amount = (
                                self.data.positions[y.key].collateral_amount
                                - (
                                    sp.mul(
                                        y.value.position_value,
                                        self.data.long_funding_rate.value,
                                    )
                                )
                                / self.data.decimal
                            )
                if self.data.total_short > 0:
                    for x in self.data.positions.items():
                        if x.value.position == 2:
                            self.data.positions[x.key].funding_amount += (
                                sp.mul(
                                    x.value.position_value,
                                    self.data.short_funding_rate.value,
                                )
                            ) / self.data.decimal
                            self.data.positions[x.key].collateral_amount += (
                                sp.mul(
                                    x.value.position_value,
                                    self.data.short_funding_rate.value,
                                )
                            ) / self.data.decimal
            self.data.previous_funding_time = sp.now
            self.data.upcoming_funding_time = sp.add_seconds(
                sp.now, self.data.funding_period
            )
            self.data.current_mark_price = (
                self.data.vmm.usd_amount * self.data.decimal
            ) / self.data.vmm.token_amount
            sp.emit(sp.record(funding_time=sp.now), tag="FUNDING_DISTRIBUTED")

        @sp.entrypoint
        def increasePosition(self, direction, usd_amount, leverage_multiple):
            """
            Increase the position by adding more funds to an existing position or open a new position.

            Args:
                direction (int): The direction of the position (1 for long, 2 for short).
                usd_amount (int): The amount of USD to be added to the position.
                leverage_multiple (int): The leverage multiple for the position.
            """
            sp.cast(direction, sp.int)
            sp.cast(usd_amount, sp.int)
            sp.cast(leverage_multiple, sp.int)

            assert direction == sp.int(1) or direction == sp.int(2), "INVALID_DIRECTION"
            assert usd_amount >= sp.int(0) * self.data.decimal, "INVALID_USD_AMOUNT"
            assert (
                leverage_multiple >= sp.int(0) * self.data.decimal
            ), "INVALID_LEVERAGE_AMOUNT"

            self.updateIndexPrice()
            self.transferUsd(
                sp.record(
                    sender_=sp.sender,
                    receiver_=sp.self_address(),
                    amount_=abs(usd_amount),
                )
            )

            net_usd_amount = (
                usd_amount - (usd_amount * self.data.transaction_fees) / 100
            )

            if direction == sp.int(1):
                position_value = abs(
                    self.data.vmm.invariant
                    * self.data.decimal
                    / (
                        self.data.vmm.usd_amount
                        + (sp.mul(leverage_multiple, net_usd_amount))
                    )
                    - self.data.vmm.token_amount
                )
                if self.data.positions.contains(sp.sender) == False:
                    self.data.positions[sp.sender] = sp.record(
                        position=direction,
                        entry_price=self.data.current_mark_price,
                        funding_amount=sp.int(0),
                        position_value=sp.to_int(position_value),
                        collateral_amount=net_usd_amount,
                        usd_amount=sp.mul(net_usd_amount, leverage_multiple),
                    )
                    self.data.vmm.usd_amount += sp.mul(
                        net_usd_amount, leverage_multiple
                    )
                    self.data.vmm.token_amount = self.data.vmm.token_amount - sp.to_int(
                        position_value
                    )
                    sp.emit(
                        sp.record(
                            position_value=sp.to_int(position_value),
                            collateral_amount=net_usd_amount,
                            usd_amount=sp.mul(net_usd_amount, leverage_multiple),
                            token_amount=(
                                self.data.vmm.token_amount - sp.to_int(position_value)
                            ),
                            position_holder=sp.sender,
                        ),
                        tag="LONG_POSITION_OPENED",
                    )
                else:
                    assert (
                        self.data.positions[sp.sender].position == 1
                    ), "INVALID_POSITION"
                    self.data.positions[sp.sender].entry_price = (
                        self.data.positions[sp.sender].entry_price
                        + self.data.current_mark_price
                    ) / 2
                    self.data.positions[sp.sender].position_value += sp.to_int(
                        position_value
                    )
                    self.data.positions[sp.sender].collateral_amount += net_usd_amount
                    self.data.positions[sp.sender].usd_amount += sp.mul(
                        net_usd_amount, leverage_multiple
                    )
                    self.data.vmm.usd_amount += sp.mul(
                        net_usd_amount, leverage_multiple
                    )
                    self.data.vmm.token_amount = self.data.vmm.token_amount - (
                        sp.to_int(position_value)
                    )
                    sp.emit(
                        sp.record(
                            position_value=self.data.positions[
                                sp.sender
                            ].position_value,
                            collateral_amount=self.data.positions[
                                sp.sender
                            ].collateral_amount,
                            usd_amount=self.data.positions[sp.sender].usd_amount,
                            token_amount=self.data.vmm.token_amount
                            - sp.to_int(position_value),
                            position_holder=sp.sender,
                        ),
                        tag="LONG_POSITION_INCREASED",
                    )
                self.data.total_long += sp.to_int(position_value)

            else:
                if direction == sp.int(2):
                    position_value = (
                        self.data.vmm.invariant
                        * self.data.decimal
                        / (
                            (
                                self.data.vmm.usd_amount
                                - (sp.mul(leverage_multiple, net_usd_amount))
                            )
                        )
                        - self.data.vmm.token_amount
                    )
                    if self.data.positions.contains(sp.sender) == False:
                        self.data.positions[sp.sender] = sp.record(
                            position=sp.int(2),
                            entry_price=self.data.current_mark_price,
                            funding_amount=sp.int(0),
                            position_value=(position_value),
                            collateral_amount=net_usd_amount,
                            usd_amount=sp.mul(net_usd_amount, leverage_multiple),
                        )
                        self.data.vmm.usd_amount = self.data.vmm.usd_amount - sp.mul(
                            net_usd_amount, leverage_multiple
                        )
                        self.data.vmm.token_amount += position_value
                        sp.emit(
                            sp.record(
                                position_value=(position_value),
                                collateral_amount=net_usd_amount,
                                usd_amount=sp.mul(net_usd_amount, leverage_multiple),
                                token_amount=(position_value),
                                position_holder=sp.sender,
                            ),
                            tag="SHORT_POSITION_OPENED",
                        )
                    else:
                        assert (
                            self.data.positions[sp.sender].position == 2
                        ), "INVALID_POSITION"
                        self.data.positions[sp.sender].entry_price = (
                            self.data.positions[sp.sender].entry_price
                            + self.data.current_mark_price
                        ) / 2
                        self.data.positions[sp.sender].position_value += position_value
                        self.data.positions[
                            sp.sender
                        ].collateral_amount += net_usd_amount
                        self.data.positions[sp.sender].usd_amount += sp.mul(
                            net_usd_amount, leverage_multiple
                        )
                        self.data.vmm.usd_amount = self.data.vmm.usd_amount - sp.mul(
                            net_usd_amount, leverage_multiple
                        )
                        self.data.vmm.token_amount += position_value
                        sp.emit(
                            sp.record(
                                position_value=self.data.positions[
                                    sp.sender
                                ].position_value,
                                collateral_amount=self.data.positions[
                                    sp.sender
                                ].collateral_amount,
                                usd_amount=self.data.positions[sp.sender].usd_amount,
                                token_amount=(position_value),
                                position_holder=sp.sender,
                            ),
                            tag="SHORT_POSITION_INCREASED",
                        )
                    self.data.total_short += position_value

                else:
                    raise "INVALID_DIRECTION"

            self.transferUsd(
                sp.record(
                    sender_=sp.self_address(),
                    receiver_=self.data.administration_panel.fundManager,
                    amount_=abs(usd_amount - net_usd_amount),
                )
            )

            self.data.current_mark_price = (
                self.data.vmm.usd_amount * self.data.decimal
            ) / self.data.vmm.token_amount

        @sp.entrypoint
        def closePosition(self):
            """
            Close the position of the sender.

            This function closes the position of the sender by performing the necessary calculations and transferring the appropriate amount of USD tokens.

            Raises:
                AssertionError: If the sender's position is not found.

            Emits:
                LONG_POSITION_CLOSED: If the sender's position is long.
                SHORT_POSITION_CLOSED: If the sender's position is short.
            """

            assert self.data.positions.contains(sp.sender), "POSITION_NOT_FOUND"
            self.updateIndexPrice()

            if self.data.positions[sp.sender].position == 1:
                position_value = self.data.vmm.usd_amount - (
                    self.data.vmm.invariant
                    * self.data.decimal
                    / (
                        self.data.vmm.token_amount
                        + self.data.positions[sp.sender].position_value
                    )
                )

                pnl = position_value - (self.data.positions[sp.sender].usd_amount)

                self.transferUsd(
                    sp.record(
                        sender_=sp.self_address(),
                        receiver_=sp.sender,
                        amount_=abs(
                            self.data.positions[sp.sender].collateral_amount + pnl
                        ),
                    )
                )

                self.data.vmm.usd_amount = self.data.vmm.usd_amount - position_value
                self.data.vmm.token_amount += self.data.positions[
                    sp.sender
                ].position_value
                self.data.total_long = (
                    self.data.total_long - self.data.positions[sp.sender].position_value
                )
                del self.data.positions[sp.sender]
                self.data.current_mark_price = (
                    self.data.vmm.usd_amount * self.data.decimal
                ) / self.data.vmm.token_amount
                sp.emit(
                    sp.record(pnl=pnl, position_holder=sp.sender),
                    tag="LONG_POSITION_CLOSED",
                )

            else:
                if self.data.positions[sp.sender].position == 2:
                    position_value = (
                        self.data.vmm.invariant
                        * self.data.decimal
                        / (
                            self.data.vmm.token_amount
                            - self.data.positions[sp.sender].position_value
                        )
                    ) - self.data.vmm.usd_amount
                    pnl = self.data.positions[sp.sender].usd_amount - position_value

                    self.transferUsd(
                        sp.record(
                            sender_=sp.self_address(),
                            receiver_=sp.sender,
                            amount_=abs(
                                self.data.positions[sp.sender].collateral_amount + pnl
                            ),
                        )
                    )
                    self.data.vmm.usd_amount += position_value
                    self.data.vmm.token_amount = (
                        self.data.vmm.token_amount
                        - self.data.positions[sp.sender].position_value
                    )
                    self.data.total_short = (
                        self.data.total_short
                        - self.data.positions[sp.sender].position_value
                    )
                    del self.data.positions[sp.sender]
                    self.data.current_mark_price = (
                        self.data.vmm.usd_amount * self.data.decimal
                    ) / self.data.vmm.token_amount
                    sp.emit(
                        sp.record(pnl=pnl, position_holder=sp.sender),
                        tag="SHORT_POSITION_CLOSED",
                    )

        @sp.entrypoint
        def addMargin(self, amount):
            """
            Adds margin to the original position.

            :param amount: The amount of margin to be added.
            """
            sp.cast(amount, sp.int)

            self.updateIndexPrice()
            amount1 = amount - (amount * self.data.transaction_fees) / 100
            self.transferUsd(
                sp.record(
                    sender_=sp.sender,
                    receiver_=sp.self_address(),
                    amount_=abs(amount),
                )
            )
            self.data.positions[sp.sender].collateral_amount += amount1
            self.data.current_mark_price = (
                self.data.vmm.usd_amount * self.data.decimal
            ) / self.data.vmm.token_amount
            self.transferUsd(
                sp.record(
                    sender_=sp.self_address(),
                    receiver_=self.data.administration_panel.fundManager,
                    amount_=abs(amount - amount1),
                )
            )
            sp.emit(
                sp.record(amount=amount1, position_holder=sp.sender),
                tag="MARGIN_ADDED",
            )

        @sp.entrypoint
        def removeMargin(self, amount):
            """
            Removes the specified amount of margin from the sender's position.

            :param amount: The amount of margin to be removed.
            """

            sp.cast(amount, sp.int)
            self.updateIndexPrice()
            margin_ratio = (
                (self.data.positions[sp.sender].collateral_amount - amount)
                * self.data.decimal
                / self.data.positions[sp.sender].usd_amount
            )
            assert margin_ratio > ((30 * self.data.decimal) / 100), "INVALID_MARGIN"
            self.transferUsd(
                sp.record(
                    sender_=sp.self_address(), receiver_=sp.sender, amount_=abs(amount)
                )
            )
            self.data.positions[sp.sender].collateral_amount = (
                self.data.positions[sp.sender].collateral_amount - amount
            )
            self.data.current_mark_price = (
                self.data.vmm.usd_amount * self.data.decimal
            ) / self.data.vmm.token_amount
            sp.emit(
                sp.record(amount=amount, position_holder=sp.sender),
                tag="MARGIN_REMOVED",
            )

        @sp.entrypoint
        def liquidate(self, position_holder):
            """
            Liquidates a position held by the given position_holder.

            Args:
                position_holder (sp.address): The address of the position holder.

            Raises:
                AssertionError: If the margin ratio is greater than the allowed threshold.

            Returns:
                None
            """

            sp.cast(position_holder, sp.address)
            self.updateIndexPrice()
            if self.data.positions[position_holder].position == 1:
                position_value = self.data.vmm.usd_amount - (
                    self.data.vmm.invariant
                    * self.data.decimal
                    / (
                        self.data.vmm.token_amount
                        + self.data.positions[position_holder].position_value
                    )
                )
                final_value = self.data.positions[position_holder].collateral_amount + (
                    position_value - self.data.positions[position_holder].usd_amount
                )
                if final_value > 0:
                    margin_ratio = (
                        final_value
                        * self.data.decimal
                        / self.data.positions[position_holder].usd_amount
                    )
                    assert margin_ratio < (
                        (85 * self.data.decimal) / 1000
                    ), "MARIGN_RATIO_GREATER"

                self.data.vmm.usd_amount = self.data.vmm.usd_amount - position_value
                self.data.vmm.token_amount += self.data.positions[
                    position_holder
                ].position_value
                self.data.current_mark_price = (
                    self.data.vmm.usd_amount * self.data.decimal
                ) / self.data.vmm.token_amount
                self.data.total_long = (
                    self.data.total_long
                    - self.data.positions[position_holder].position_value
                )
                self.transferUsd(
                    sp.record(
                        sender_=sp.self_address(),
                        receiver_=sp.sender,
                        amount_=abs(abs(final_value) - (abs(final_value) * 3) / 100),
                    )
                )
                self.transferUsd(
                    sp.record(
                        sender_=sp.self_address(),
                        receiver_=self.data.administration_panel.fundManager,
                        amount_=(abs(final_value) * 3) / 100,
                    )
                )
                del self.data.positions[position_holder]

            else:
                if self.data.positions[position_holder].position == 2:
                    position_value = (
                        self.data.vmm.invariant
                        * self.data.decimal
                        / (
                            self.data.vmm.token_amount
                            - self.data.positions[position_holder].position_value
                        )
                        - self.data.vmm.usd_amount
                    )
                    final_value = (
                        self.data.positions[position_holder].collateral_amount
                    ) + (
                        (self.data.positions[position_holder].usd_amount)
                        - position_value
                    )
                    if final_value > 0:
                        margin_ratio = (
                            final_value
                            * self.data.decimal
                            / self.data.positions[position_holder].usd_amount
                        )
                        assert margin_ratio < (
                            (85 * self.data.decimal) / 1000
                        ), "MARIGN_RATIO_GREATER"

                    self.data.vmm.usd_amount += position_value
                    self.data.vmm.token_amount = (
                        self.data.vmm.token_amount
                        - self.data.positions[position_holder].position_value
                    )
                    self.data.current_mark_price = (
                        self.data.vmm.usd_amount * self.data.decimal
                    ) / self.data.vmm.token_amount
                    self.data.total_short = (
                        self.data.total_short
                        - self.data.positions[position_holder].position_value
                    )
                    self.transferUsd(
                        sp.record(
                            sender_=sp.self_address(),
                            receiver_=position_holder,
                            amount_=abs(abs(final_value) - abs(final_value * 3) / 100),
                        )
                    )
                    self.transferUsd(
                        sp.record(
                            sender_=sp.self_address(),
                            receiver_=self.data.administration_panel.fundManager,
                            amount_=(abs(final_value) * 3) / 100,
                        )
                    )
                    del self.data.positions[position_holder]
            sp.emit(
                sp.record(position_holder=position_holder), tag="POSITION_LIQUIDATED"
            )

        @sp.entrypoint
        def decreasePosition(self, usd_amount, leverage_multiple):
            """
            Decreases the position of the sender by the specified USD amount and leverage multiple.

            Args:
                usd_amount (int): The amount in USD to decrease the position by.
                leverage_multiple (int): The leverage multiple to apply to the USD amount.

            Raises:
                AssertionError: If the contract is paused.
                AssertionError: If the sender does not have a position.
                AssertionError: If the leverage multiple is not greater than 0.
                AssertionError: If the USD amount is not greater than 0.
                AssertionError: If the position value is less than the calculated decrease.

            Returns:
                None
            """

            sp.cast(leverage_multiple, sp.int)
            sp.cast(usd_amount, sp.int)
            assert self.data.positions.contains(sp.sender), "POSITION_NOT_FOUND"
            assert leverage_multiple > 0, "LEVERAGE_MULTIPLE_INVALID"
            assert usd_amount > 0, "POSITION_AMOUNT_INVALID"
            self.updateIndexPrice()

            if self.data.positions[sp.sender].position == 1:
                position_value = abs(
                    self.data.vmm.invariant
                    * self.data.decimal
                    / (
                        self.data.vmm.usd_amount
                        + (sp.mul(leverage_multiple, usd_amount))
                    )
                    - self.data.vmm.token_amount
                )
                assert self.data.positions[sp.sender].position_value >= (
                    sp.to_int(position_value)
                ), "DECREASE_MORE_THAN_ACTUAL_POSITION"

                self.data.positions[sp.sender].position_value = self.data.positions[
                    sp.sender
                ].position_value - sp.to_int(position_value)
                self.data.positions[sp.sender].usd_amount = self.data.positions[
                    sp.sender
                ].usd_amount - sp.mul(usd_amount, leverage_multiple)
                self.data.total_long = self.data.total_long - sp.to_int(position_value)
                self.data.vmm.token_amount += sp.to_int(position_value)
                self.data.vmm.usd_amount = self.data.vmm.usd_amount - sp.mul(
                    usd_amount, leverage_multiple
                )
                self.data.current_mark_price = (
                    self.data.vmm.usd_amount * self.data.decimal
                ) / self.data.vmm.token_amount
                sp.emit(
                    sp.record(
                        position_value=self.data.positions[sp.sender].position_value,
                        collateral_amount=self.data.positions[
                            sp.sender
                        ].collateral_amount,
                        usd_amount=self.data.positions[sp.sender].usd_amount,
                        token_amount=(position_value),
                        position_holder=sp.sender,
                    ),
                    tag="LONG_POSITION_DECREASED",
                )
                self.transferUsd(
                    sp.record(
                        sender_=sp.self_address(),
                        receiver_=sp.sender,
                        amount_=position_value,
                    )
                )

            if self.data.positions[sp.sender].position == 2:
                position_value = abs(
                    self.data.vmm.invariant
                    * self.data.decimal
                    / (
                        self.data.vmm.usd_amount
                        + (sp.mul(leverage_multiple, usd_amount))
                    )
                    - self.data.vmm.token_amount
                )
                assert self.data.positions[sp.sender].position_value >= sp.to_int(
                    position_value
                ), "DECREASE_MORE_THAN_ACTUAL_POSITION"

                self.data.positions[sp.sender].position_value = self.data.positions[
                    sp.sender
                ].position_value - sp.to_int(position_value)
                self.data.positions[sp.sender].usd_amount = self.data.positions[
                    sp.sender
                ].usd_amount - sp.mul(usd_amount, leverage_multiple)
                self.data.total_short = self.data.total_short - sp.to_int(
                    position_value
                )
                self.data.vmm.token_amount = self.data.vmm.token_amount - sp.to_int(
                    position_value
                )
                self.data.vmm.usd_amount += sp.mul(usd_amount, leverage_multiple)
                self.data.current_mark_price = (
                    self.data.vmm.usd_amount * self.data.decimal
                ) / self.data.vmm.token_amount
                sp.emit(
                    sp.record(
                        position_value=self.data.positions[sp.sender].position_value,
                        collateral_amount=self.data.positions[
                            sp.sender
                        ].collateral_amount,
                        usd_amount=self.data.positions[sp.sender].usd_amount,
                        token_amount=abs(
                            self.data.vmm.token_amount - sp.to_int(position_value)
                        ),
                        position_holder=sp.sender,
                    ),
                    tag="SHORT_POSITION_DECREASED",
                )

                self.transferUsd(
                    sp.record(
                        sender_=sp.self_address(),
                        receiver_=sp.sender,
                        amount_=position_value,
                    )
                )


# Tests
if __name__ == "__main__":

    @sp.add_test()
    def test():
        sc = sp.test_scenario("vmm_test", [vmm_types, sp.utils, helpers, vmm])
        sc.h1("VMM Contract")

        # Originate the contract
        sc.h2("Originate VMM Contract")
        vmm_core = vmm.VMM(
            metadata=sp.scenario_utils.metadata_of_url("https://example.com"),
            administrator=Address.alice,
            fund_manager=Address.elon,
            usd_contract_address=Address.usdt,
            oracle_address=Address.oracle,
        )
        sc += vmm_core

        # Show Initial Storage
        sc.h1("Initial Storage")
        sc.show(vmm_core.data)
