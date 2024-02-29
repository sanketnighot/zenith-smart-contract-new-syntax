import smartpy as sp  # type: ignore


@sp.module
def helpers():
    transfer_params_type: type = sp.list[
        sp.record(
            from_=sp.address,
            txs=sp.list[
                sp.record(to_=sp.address, amount=sp.nat, token_id=sp.nat).layout(
                    ("to_", ("token_id", "amount"))
                )
            ],
        ).layout(("from_", "txs")),
    ]

    class Helpers(sp.Contract):
        def __init__(self, oracle_address, usd_contract_address):
            self.data.current_index_price = sp.cast(0, sp.int)
            self.data.current_mark_price = sp.cast(0, sp.int)
            self.data.oracle_address = sp.cast(oracle_address, sp.address)
            self.data.usd_contract_address = sp.cast(usd_contract_address, sp.address)
            self.data.decimal = sp.cast(1000000, sp.int)
            self.data.short_funding_rate = sp.cast(
                sp.record(value=0, direction="NA"),
                sp.record(value=sp.int, direction=sp.string),
            )
            self.data.long_funding_rate = sp.cast(
                sp.record(value=0, direction="NA"),
                sp.record(value=sp.int, direction=sp.string),
            )
            self.data.total_long = sp.cast(0, sp.int)
            self.data.total_short = sp.cast(0, sp.int)

        @sp.private(with_storage="read-write")
        def updateIndexPrice(self):
            oracle_data = sp.view(
                "getlastCompletedData",
                self.data.oracle_address,
                (),
                sp.record(
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
                ),
            ).unwrap_some()
            assert sp.now - oracle_data.lastUpdatedAt <= sp.int(
                600
            ), "Oracle Data Expired"

            self.data.current_index_price = sp.to_int(oracle_data.data)

        @sp.private(with_storage="read-write", with_operations=True)
        def transferUsd(self, params):
            sp.cast(
                params,
                sp.record(
                    sender_=sp.address,
                    receiver_=sp.address,
                    amount_=sp.nat,
                ),
            )
            contractParams = sp.contract(
                transfer_params_type,
                self.data.usd_contract_address,
                "transfer",
            ).unwrap_some()

            dataToBeSent = sp.cast(
                [
                    sp.record(
                        from_=params.sender_,
                        txs=[
                            sp.record(
                                to_=params.receiver_,
                                amount=params.amount_,
                                token_id=sp.nat(0),
                            )
                        ],
                    )
                ],
                transfer_params_type,
            )

            sp.transfer(dataToBeSent, sp.mutez(0), contractParams)

        @sp.private(with_storage="read-write", with_operations=True)
        def calculateFundingRate(self):
            price_difference = (
                self.data.current_mark_price - self.data.current_index_price
            )
            funding_rate = price_difference / sp.int(24)
            average_value = (
                self.data.current_mark_price + self.data.current_index_price
            ) / 2
            percentage = (funding_rate * self.data.decimal * 100) / average_value
            if percentage >= (5 * self.data.decimal):
                percentage = 5 * self.data.decimal
            if price_difference > 0:
                if self.data.total_long == 0:
                    self.data.long_funding_rate.value = 0
                    self.data.long_funding_rate.direction = "NEGATIVE"
                else:
                    self.data.long_funding_rate.value = percentage
                    self.data.long_funding_rate.direction = "NEGATIVE"
                if self.data.total_short == 0:
                    self.data.short_funding_rate.value = 0
                    self.data.short_funding_rate.direction = "POSITIVE"
                else:
                    self.data.short_funding_rate.value = (
                        self.data.total_long * percentage
                    ) / self.data.total_short
                    self.data.short_funding_rate.direction = "POSITIVE"
            if price_difference < 0:
                if self.data.total_short == 0:
                    self.data.short_funding_rate.value = 0
                    self.data.short_funding_rate.direction = "NEGATIVE"
                else:
                    self.data.short_funding_rate.value = percentage
                    self.data.short_funding_rate.direction = "NEGATIVE"
                if self.data.total_long == 0:
                    self.data.long_funding_rate.value = 0
                    self.data.long_funding_rate.direction = "POSITIVE"
                else:
                    self.data.long_funding_rate.value = (
                        self.data.total_short * percentage
                    ) / self.data.total_long
                    self.data.long_funding_rate.direction = "POSITIVE"


# if __name__ == "__main__":

#     @sp.add_test("Helper")
#     def test():
#         sc = sp.test_scenario(helpers)

#         sc.h1("USDt Contract")
#         helper_contract = helpers.Helpers(
#             oracle_address=sp.address("tz1ooOracle"),
#             usd_contract_address=sp.address("tz1ooUSDt"),
#         )
#         sc += helper_contract
