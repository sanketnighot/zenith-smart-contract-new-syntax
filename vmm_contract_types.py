import smartpy as sp  # type: ignore


@sp.module
def vmm_types():
    vmm_type: type = sp.record(
        asset_amount=sp.int, token_amount=sp.int, invariant=sp.int
    )

    administration_panel_type: type = sp.record(
        administrator=sp.address,
        pending_administrator=sp.option[sp.address],
        fund_manager=sp.address,
        position_operators=sp.set[sp.address],
        paused=sp.bool,
    )

    pending_positions_type: type = sp.map[
        sp.address,
        sp.record(
            direction=sp.int,
            token_amount=sp.int,
            leverage_multiple=sp.int,
            execution_price=sp.int,
        ),
    ]

    active_positions_type: type = sp.big_map[
        sp.address,
        sp.record(
            direction=sp.int,
            entry_price=sp.int,
            position_amount=sp.int,
            collateral_amount=sp.int,
            funding_amount=sp.int,
            token_amount=sp.int,
        ),
    ]

    create_order_type: type = sp.record(
        direction=sp.int,
        token_amount=sp.int,
        leverage_multiple=sp.int,
    )
