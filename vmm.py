import sys

sys.path.insert(
    0,
    "/Users/sanket/Zenith/Projects/Testnet/zenith-smart-contract-new-syntax",
)

import smartpy as sp  # type: ignore
import utilities.Address as Address
from vmm_contract_types import vmm_types


@sp.module
def vmm():
    class VMM(sp.Contract):
        def __init__(
            self, metadata, administrator, fund_manager, token_address, oracle_address
        ):
            self.data = sp.record(
                # Metadata of the contract
                metadata=sp.cast(metadata, sp.big_map[sp.string, sp.bytes]),
                # Administration panel to handle the contract
                administration_panel=sp.cast(
                    sp.record(
                        administrator=administrator,
                        pending_administrator=None,
                        fund_manager=fund_manager,
                        position_operators=sp.set(administrator),
                        paused=False,
                    ),
                    vmm_types.administration_panel_type,
                ),
                # VMM state of the asset.
                vmm=sp.cast(
                    sp.record(
                        asset_amount=sp.int(0),
                        token_amount=sp.int(0),
                        invariant=sp.int(0),
                    ),
                    vmm_types.vmm_type,
                ),
                # Set of long positions addresses
                long_positions=sp.cast(sp.set(), sp.set[sp.address]),
                # Set of short positions addresses
                short_positions=sp.cast(sp.set(), sp.set[sp.address]),
                # All orders till now
                all_orders=sp.cast(0, sp.int),
                # Active positions data
                active_positions=sp.cast(sp.big_map(), vmm_types.active_positions_type),
                # Total long positions currently active
                total_long=sp.cast(0, sp.int),
                # Total short positions currently active
                total_short=sp.cast(0, sp.int),
                # Long funding rate of current funding period
                long_funding_rate=sp.cast(0, sp.int),
                # Short funding rate of current funding period
                short_funding_rate=sp.cast(0, sp.int),
                # Decimal precision for the contract
                decimal=sp.cast(1000000, sp.int),
                # Token address of asset used to trade
                token_address=sp.cast(token_address, sp.address),
                # Oracle address to get the index price
                oracle_address=sp.cast(oracle_address, sp.address),
                # Current index price of the asset in cex
                current_index_price=sp.cast(1200000, sp.int),
                # Current market price of the asset in vmm
                current_market_price=sp.cast(0, sp.int),
                # Next funding time to distribute funding
                next_funding_time=sp.cast(sp.timestamp(0), sp.timestamp),
                # Funding period of the contract
                funding_period=sp.cast(3600, sp.int),
                # Transaction fees for each trade
                transaction_fees=sp.cast(2, sp.int),
            )

        # Check if sender is an administrator
        @sp.private(with_storage="read-only")
        def is_administrator(self):
            assert sp.sender == self.data.administration_panel.administrator, "NotAdmin"

        # Check if contract is paused
        @sp.private(with_storage="read-only")
        def is_paused(self):
            assert not self.data.administration_panel.paused, "ContractPaused"

        # Check if sender has active position
        @sp.private(with_storage="read-only")
        def assert_no_active_position(self):
            assert not (
                self.data.long_positions.contains(sp.sender)
                or self.data.short_positions.contains(sp.sender)
            ), "AlreadyActivePosition"

        # Check if sender does not has active position
        @sp.private(with_storage="read-only")
        def assert_has_active_position(self):
            assert self.data.long_positions.contains(
                sp.sender
            ) or self.data.short_positions.contains(sp.sender), "NoActivePosition"

        # Propose a new administrator for the contract
        @sp.entrypoint
        def propose_new_administrator(self, new_administrator):
            sp.cast(new_administrator, sp.address)
            self.is_administrator()
            self.data.administration_panel.pending_administrator = sp.Some(
                new_administrator
            )

        # Accept the new administrator for the contract
        @sp.entrypoint
        def confirm_administrator_role(self):
            assert (
                self.data.administration_panel.pending_administrator
            ).unwrap_some() == sp.sender
            self.data.administration_panel.administrator = sp.sender
            self.data.administration_panel.pending_administrator = None

        # Set the fund manager for the contract
        @sp.entrypoint
        def assign_fund_manager(self, fund_manager):
            sp.cast(fund_manager, sp.address)
            self.is_administrator()
            self.data.administration_panel.fund_manager = fund_manager

        # Assign position operator for the contract
        @sp.entrypoint
        def appoint_position_operator(self, position_operator):
            sp.cast(position_operator, sp.address)
            self.is_administrator()
            self.data.administration_panel.position_operators.add(position_operator)

        # Remove position operator for the contract
        @sp.entrypoint
        def revoke_position_operator(self, position_operator):
            sp.cast(position_operator, sp.address)
            self.is_administrator()
            self.data.administration_panel.position_operators.remove(position_operator)

        # Toggle Pause of the contract
        @sp.entrypoint
        def switch_pause_state(self):
            self.is_administrator()
            self.data.administration_panel.paused = (
                not self.data.administration_panel.paused
            )

        # Set the token address for the contract
        @sp.entrypoint
        def set_token_address(self, token_address):
            sp.cast(token_address, sp.address)
            self.is_administrator()
            self.data.token_address = token_address

        # Set the oracle address for the contract
        @sp.entrypoint
        def set_oracle_address(self, oracle_address):
            sp.cast(oracle_address, sp.address)
            self.is_administrator()
            self.data.oracle_address = oracle_address

        # Set the funding period for the contract
        @sp.entrypoint
        def set_funding_period(self, funding_period):
            sp.cast(funding_period, sp.int)
            self.is_administrator()
            self.data.funding_period = funding_period

        # Set the transaction fees for the contract
        @sp.entrypoint
        def set_transaction_fees(self, transaction_fees):
            sp.cast(transaction_fees, sp.int)
            self.is_administrator()
            self.data.transaction_fees = transaction_fees

        # Set the decimal precision for the contract
        @sp.entrypoint
        def set_decimal(self, decimal):
            sp.cast(decimal, sp.int)
            self.is_administrator()
            self.data.decimal = decimal

        # Set vmm state of the contract
        @sp.entrypoint
        def initialize_vmm_parameters(self, asset_amount):
            sp.cast(asset_amount, sp.int)
            self.is_administrator()
            assert asset_amount > 0, "InvalidParameters"
            assert (
                self.data.vmm.asset_amount == 0 and self.data.vmm.token_amount == 0
            ), "VMMAlreadyInitialized"
            token_amount = (
                asset_amount * self.data.current_index_price
            ) / self.data.decimal
            self.data.vmm.asset_amount = asset_amount
            self.data.vmm.token_amount = token_amount
            self.data.vmm.invariant = sp.mul(asset_amount, token_amount)
            self.data.current_market_price = (
                self.data.vmm.token_amount * self.data.decimal
            ) / self.data.vmm.asset_amount
            self.data.next_funding_time = sp.add_seconds(
                sp.now, self.data.funding_period
            )
            sp.emit(self.data.vmm, tag="VMM_CONFIGURED")

        @sp.entrypoint
        def set_current_index_price(self, current_index_price):
            sp.cast(current_index_price, sp.int)
            self.is_administrator()
            self.data.current_index_price = current_index_price


if __name__ == "__main__":

    @sp.add_test("VMM Compiled Contract")
    def test():
        sc = sp.test_scenario([vmm_types, vmm])
        sc.h1("VMM Contract")

        # Originate the contract
        sc.h2("Originate VMM Contract")
        vmm_contract = vmm.VMM(
            metadata=sp.utils.metadata_of_url("https://example.com"),
            administrator=Address.admin,
            fund_manager=Address.elon,
            token_address=Address.usdt,
            oracle_address=Address.oracle,
        )
        sc += vmm_contract
        sc.show(vmm_contract.data)

    @sp.add_test("VMM Initialize VMM Parameters")
    def test():
        sc = sp.test_scenario([vmm_types, vmm])
        sc.h1("VMM Contract")

        # Originate the contract
        sc.h2("Originate VMM Contract")
        vmm_contract = vmm.VMM(
            metadata=sp.utils.metadata_of_url("https://example.com"),
            administrator=Address.admin,
            fund_manager=Address.elon,
            token_address=Address.usdt,
            oracle_address=Address.oracle,
        )
        sc += vmm_contract

        # Test Initialize VMM Parameters
        vmm_contract.initialize_vmm_parameters(sp.int(100000000)).run(
            sender=Address.admin
        )
        vmm_contract.initialize_vmm_parameters(sp.int(100000)).run(
            sender=Address.admin, valid=False
        )
        sc.show(vmm_contract.data)

    @sp.add_test("Testing Positions Entrypoint")
    def test():
        sc = sp.test_scenario([vmm_types, vmm])
        sc.h1("VMM Contract")

        # Originate the contract
        sc.h2("Originate VMM Contract")
        vmm_contract = vmm.VMM(
            metadata=sp.utils.metadata_of_url("https://example.com"),
            administrator=Address.admin,
            fund_manager=Address.elon,
            token_address=Address.usdt,
            oracle_address=Address.oracle,
        )
        sc += vmm_contract

        # Test Initialize VMM Parameters
        vmm_contract.initialize_vmm_parameters(sp.int(100000000)).run(
            sender=Address.admin
        )
        sc.show(vmm_contract.data)
