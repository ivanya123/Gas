import asyncio
import datetime
import json
import pandas as pd
import os

from tinkoff.invest.utils import now
from tinkoff.invest import (
    AsyncClient,
    CandleInstrument,
    MarketDataRequest,
    SubscribeCandlesRequest,
    SubscriptionAction,
    SubscriptionInterval, Quotation, CandleInterval
)

from CONSTANTS import TOKEN
from function_processing import get_increment_amount, get_instrument_info

min_increment = 0.001
min_price_amount = 1
ticker = 'NGZ4'


def to_price(quotation: Quotation):
    return quotation.units + quotation.nano / 1_000_000_000


async def main():

    async with AsyncClient(TOKEN) as client:
        candle_list = []
        async for candle in client.get_all_candles(
                instrument_id='2f52fac0-36a0-4e7c-82f4-2f87beed762f',
                from_=now() - datetime.timedelta(days=365),
                interval=CandleInterval.CANDLE_INTERVAL_HOUR
        ):
            row = {
                'time': candle.time,
                'open': to_price(candle.open),
                'high': to_price(candle.high),
                'low': to_price(candle.low),
                'close': to_price(candle.close),
                'volume': candle.volume
            }
            candle_list.append(row)
            print(candle)
        else:
            df = pd.DataFrame(candle_list)
            df.to_csv('candles_january___1.csv', index=False)

if __name__ == "__main__":
    asyncio.run(main())
