import datetime
from decimal import Decimal
import pickle as pkl
import os

import pandas as pd

from trad.connect_tinkoff import ConnectTinkoff
from download_futers.historic_future import HistoricInstrument
import asyncio
from config import TOKEN


async def main():
    connect = ConnectTinkoff(TOKEN)
    task = asyncio.create_task(connect.get_candles_from_ticker('BMH5', '1h'))
    task_2 = asyncio.create_task(connect.get_candles_from_ticker('CCH5', '1h'))
    brent_candles, instrument_brent = await task
    cacao_candles, instrument_cacao = await task_2
    futures_brent = HistoricInstrument(list_candles=brent_candles, instrument=instrument_brent)
    futures_cacao = HistoricInstrument(list_candles=cacao_candles, instrument=instrument_cacao)
    if os.path.exists(f'{instrument_brent.name.split()[0]}'):
        pass
    else:
        os.mkdir(f'{instrument_brent.name.split()[0]}')
    path = os.path.join(f'{instrument_brent.name.split()[0]}', f'{instrument_brent.ticker}_brent')
    futures_brent.save_to_csv(path, index=False)
    if os.path.exists(f'{instrument_cacao.name.split()[0]}'):
        pass
    else:
        os.mkdir(f'{instrument_cacao.name.split()[0]}')
    path = os.path.join(f'{instrument_cacao.name.split()[0]}', f'{instrument_cacao.ticker}_cacao')
    futures_cacao.save_to_csv(path, index=False)


async def update(connect: ConnectTinkoff):
    dict_instruments_time = {}
    k = 0
    while True:
        time_now = pd.to_datetime(datetime.datetime.now(datetime.timezone.utc))
        if k == 0:
            print('Обновляем данные')
            historic_cocoa = asyncio.create_task(connect.get_candles_from_ticker('CCH5', '1h'))
            historic_brent = asyncio.create_task(connect.get_candles_from_ticker('BMH5', '1h'))
            historic_cocoa, instrument_cocoa = await historic_cocoa
            historic_brent, instrument_brent = await historic_brent
            historic_cocoa = HistoricInstrument(list_candles=historic_cocoa, instrument=instrument_cocoa)
            historic_brent = HistoricInstrument(list_candles=historic_brent, instrument=instrument_brent)
            dict_instruments_time[historic_brent.instrument_info.uid] = historic_brent.time_last_candle
            dict_instruments_time[historic_cocoa.instrument_info.uid] = historic_cocoa.time_last_candle
            historic_brent.save_to_csv(r'C:\Users\aples\PycharmProjects\Gas\trad\BRM-3.25\BMH5_brent')
            historic_cocoa.save_to_csv(r'C:\Users\aples\PycharmProjects\Gas\trad\COCOA-3.25\CCH5_cacao')
            print('Данные обновлены: ', dict_instruments_time, '\n')

        for key, value in dict_instruments_time.items():
            if value.floor('h') < time_now.floor('h'):
                print(f"Трeбуется обновление: Сейчас{time_now.floor('h')} > {value.floor('h')}")
                k = 0
                break
        else:
            k += 1
            print('Обновление не требуется')

        await asyncio.sleep(3600)


async def function():
    connect = ConnectTinkoff(TOKEN)
    await connect.connect()
    await asyncio.create_task(update(connect))
    historic_cocoa = HistoricInstrument(from_csv=True, path=r'C:\Users\aples\PycharmProjects\Gas\trad\COCOA-3.25\CCH5_cacao')


if __name__ == '__main__':
    async def m():
        connect = ConnectTinkoff(TOKEN)
        await connect.connect()
        await asyncio.create_task(update(connect))

    asyncio.run(m())