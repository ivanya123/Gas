import asyncio
import csv
import datetime
import pandas as pd
from decimal import Decimal

from tinkoff.invest import (
    AsyncClient,
    MarketDataRequest,
    SubscribeCandlesRequest,
    SubscriptionAction,
    CandleInstrument,
    SubscriptionInterval,
    Quotation,
    InstrumentIdType, SubscribeOrderBookRequest, OrderBookInstrument, OrderBook, CandleInterval, FuturesResponse,
    InstrumentStatus, )
from tinkoff.invest.utils import now

from CONSTANTS import TOKEN
from function_processing import create_dict_row_from_response


def to_price(quotation: Quotation):
    return quotation.units + quotation.nano / 1_000_000_000


async def create_csv(instrument_id: str, expiration_date: datetime.datetime, ticker: str):
    async with AsyncClient(TOKEN) as client:
        candle_list = []
        async for candle in client.get_all_candles(
                instrument_id=instrument_id,
                to=expiration_date,
                from_=expiration_date - datetime.timedelta(days=365),
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
        else:
            df = pd.DataFrame(candle_list)
            df.to_csv(f'{ticker}.csv', index=False)


async def get_futures_list():
    async with AsyncClient(TOKEN) as client:
        all_instruments: FuturesResponse = await client.instruments.futures(instrument_status=InstrumentStatus(2))
        b = [x for x in all_instruments.instruments if 'NG' in x.ticker]
        for instrument in b:
            await create_csv(instrument.uid, instrument.expiration_date, instrument.ticker)




if __name__ == '__main__':
    asyncio.run(get_futures_list())
