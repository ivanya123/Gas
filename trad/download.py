import asyncio
import datetime
import enum

import pandas as pd
import os

from tinkoff.invest import (
    AsyncClient,
    Quotation,
    CandleInterval,
    FuturesResponse,
    InstrumentStatus,
    Future)
from tinkoff.invest.utils import now

from CONSTANTS import TOKEN
from function_processing import create_dict_row_from_response
from trad.obj import DataFutures


def to_price(quotation: Quotation):
    return quotation.units + quotation.nano / 1_000_000_000


def string_to_interval(interval: str):
    dict_result = {
        '1m': CandleInterval.CANDLE_INTERVAL_1_MIN,
        '2m': CandleInterval.CANDLE_INTERVAL_2_MIN,
        '3m': CandleInterval.CANDLE_INTERVAL_3_MIN,
        '5m': CandleInterval.CANDLE_INTERVAL_5_MIN,
        '10m': CandleInterval.CANDLE_INTERVAL_10_MIN,
        '15m': CandleInterval.CANDLE_INTERVAL_15_MIN,
        '30m': CandleInterval.CANDLE_INTERVAL_30_MIN,
        '1h': CandleInterval.CANDLE_INTERVAL_HOUR,
        '2h': CandleInterval.CANDLE_INTERVAL_2_HOUR,
        '4h': CandleInterval.CANDLE_INTERVAL_4_HOUR,
        '1d': CandleInterval.CANDLE_INTERVAL_DAY,
        '1w': CandleInterval.CANDLE_INTERVAL_WEEK,
        '1M': CandleInterval.CANDLE_INTERVAL_MONTH
    }
    if interval in dict_result:
        return dict_result[interval]
    else:
        raise ValueError(f'Введите интервал в формате 1m, 2m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M')


async def download_instrument(ticker: str, interval: CandleInterval) -> tuple[pd.DataFrame, Future]:
    interval = string_to_interval(interval)
    async with AsyncClient(TOKEN) as client:
        instrument = await client.instruments.futures()
        instrument: Future = [x for x in instrument.instruments if x.ticker == ticker][0]
        list_candles = []
        async for candle in client.get_all_candles(
                instrument_id=instrument.uid,
                to=instrument.expiration_date,
                from_=instrument.expiration_date - datetime.timedelta(days=365),
                interval=interval
        ):
            row = {
                'time': candle.time,
                'open': to_price(candle.open),
                'high': to_price(candle.high),
                'low': to_price(candle.low),
                'close': to_price(candle.close),
                'volume': candle.volume
            }
            list_candles.append(row)
        data = DataFutures(list_candles)
        return data, instrument


def check_ticker_in_folder(ticker: str, folder: str = None) -> bool:
    return os.path.exists(f'{ticker}.csv')


def main_function(ticker: str, interval: str):
    pass



if __name__ == '__main__':
    asyncio.run(download_instrument(ticker='BRG5'))
    check_ticker_in_folder('BRG5')
