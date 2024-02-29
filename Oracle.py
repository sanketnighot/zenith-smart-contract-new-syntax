import smartpy as sp  # type: ignore


@sp.module
def oracle():
    price_type: type = sp.record(
        round=sp.nat,
        epoch=sp.nat,
        data=sp.nat,
        percentOracleResponse=sp.nat,
        decimals=sp.nat,
        lastUpdatedAt=sp.timestamp,
    ).layout(
        (
            "round",
            (
                "epoch",
                (
                    "data",
                    (
                        "percentOracleResponse",
                        ("decimals", "lastUpdatedAt"),
                    ),
                ),
            ),
        )
    )

    class Oracle(sp.Contract):
        def __init__(self):
            self.data.price = sp.cast(
                sp.record(
                    round=0,
                    epoch=0,
                    data=0,
                    percentOracleResponse=0,
                    decimals=0,
                    lastUpdatedAt=sp.timestamp(0),
                ),
                price_type,
            )

        @sp.entrypoint
        def updatePrice(self, data):
            self.data.price.data = data
            self.data.price.lastUpdatedAt = sp.now

        @sp.onchain_view()
        def getlastCompletedData(self):
            return sp.cast(
                sp.record(
                    round=self.data.price.round,
                    epoch=self.data.price.epoch,
                    data=self.data.price.data,
                    percentOracleResponse=self.data.price.percentOracleResponse,
                    decimals=self.data.price.decimals,
                    lastUpdatedAt=self.data.price.lastUpdatedAt,
                ),
                price_type,
            )


if __name__ == "__main__":

    @sp.add_test("oracle")
    def test():
        sc = sp.test_scenario(oracle)
        sc.h1("Oracle Contract")
        oracle_contract = oracle.Oracle()
        sc += oracle_contract
        oracle_contract.updatePrice(sp.nat(1_000_000))
