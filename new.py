import asyncio

from tinkoff.invest import (
    AsyncClient,
    CandleInstrument,
    MarketDataRequest,
    SubscribeCandlesRequest,
    SubscriptionAction,
    SubscriptionInterval, Quotation
)

from CONSTANTS import TOKEN, CLASS_CODE
from function_processing import get_increment_amount, get_instrument_info

min_increment = 0.001
min_price_amount = 1
ticker = 'NGZ4'


def to_price(quotation: Quotation):
    quotation = abs(quotation)
    return quotation.units + quotation.nano / 1_000_000_000


async def main():
    async def request_iterator():
        yield MarketDataRequest(
            subscribe_candles_request=SubscribeCandlesRequest(
                subscription_action=SubscriptionAction.SUBSCRIPTION_ACTION_SUBSCRIBE,
                instruments=[
                    CandleInstrument(
                        figi="FUTNG1224000",
                        interval=SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE,
                    )
                ],
            )
        )
        while True:
            await asyncio.sleep(1)

    async with AsyncClient(TOKEN) as client:

        min_price_amount = await get_increment_amount(client, '2f52fac0-36a0-4e7c-82f4-2f87beed762f')
        futures = await get_instrument_info(client, ticker, CLASS_CODE)
        async for marketdata in client.market_data_stream.market_data_stream(
                request_iterator()
        ):
            if marketdata.candle:
                print((to_price(marketdata.candle.close) / min_increment) * min_price_amount)
                print(futures)
                print()


if __name__ == "__main__":
    asyncio.run(main())
