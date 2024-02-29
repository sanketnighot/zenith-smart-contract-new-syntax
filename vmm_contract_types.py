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
        direction=sp.int,
        tokenAmount=sp.int,
        leverageMultiple=sp.int,
    )
