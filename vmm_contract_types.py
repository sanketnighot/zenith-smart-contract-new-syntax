import smartpy as sp  # type: ignore


@sp.module
def vmm_types():

    administration_panel_type: type = sp.record(
        administrator=sp.address,
        pendingAdministrator=sp.option[sp.address],
        positionManagers=sp.set[sp.address],
        fundManager=sp.address,
    )

    positions_value: type = sp.record(
        position=sp.int,
        entry_price=sp.int,
        funding_amount=sp.int,
        position_value=sp.int,
        collateral_amount=sp.int,
        usd_amount=sp.int,
    )

    pending_positions_type: type = sp.map[
        sp.address,
        sp.record(
            direction=sp.int,
            tokenAmount=sp.int,
            leverageMultiple=sp.int,
            executionPrice=sp.int,
        ),
    ]

    active_positions_type: type = sp.big_map[
        sp.address,
        sp.record(
            direction=sp.int,
            entryPrice=sp.int,
            positionAmount=sp.int,
            collateralAmount=sp.int,
            fundingAmount=sp.int,
            tokenAmount=sp.int,
        ),
    ]

    create_order_type: type = sp.record(
        position_holder=sp.address,
        vmm_address=sp.address,
        order_type=sp.int,  # 0: Market, 1: Limit
        trigger_price=sp.int,
        limit_price=sp.int,
        amount_in=sp.int,
        leverage_multiple=sp.int,
        direction=sp.int,
        stop_trigger_price=sp.option[sp.int],
        stop_limit_price=sp.option[sp.int],
        take_trigger_price=sp.option[sp.int],
        take_limit_price=sp.option[sp.int],
        expiration=sp.int,
        order_status=sp.int,  # 0: pending, 1: active, 2: canceled
    )
