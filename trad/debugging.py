import datetime
from decimal import Decimal
import pickle as pkl
import os

import pandas as pd
from tinkoff.invest import MarketDataResponse
from tinkoff.invest.utils import quotation_to_decimal

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


def change_dict(dict_instruments_time, *historic_futures: HistoricInstrument):
    for historic_future in historic_futures:
        dict_instruments_time[historic_future.instrument_info.uid] = historic_future.time_last_candle


async def update(connect: ConnectTinkoff,
                 dict_instruments_time: dict[str, pd.Timestamp],
                 event: asyncio.Event,
                 lock: asyncio.Lock):
    print('Вошли в функцию обновления')
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
            change_dict(dict_instruments_time, historic_brent, historic_cocoa)
            async with lock:
                historic_brent.save_to_csv(r'C:\Users\aples\PycharmProjects\Gas\trad\BRM-3.25\BMH5_brent')
                historic_cocoa.save_to_csv(r'C:\Users\aples\PycharmProjects\Gas\trad\COCOA-3.25\CCH5_cacao')
            print('Данные обновлены: ', dict_instruments_time, '\n')
            event.set()

        for key, value in dict_instruments_time.items():
            if value.floor('h') < time_now.floor('h'):
                print(f"Трeбуется обновление: Сейчас{time_now.floor('h')} > {value.floor('h')}")
                k = 0
                break
        else:
            k += 1
            print('Обновление не требуется')
            await asyncio.sleep(3600)


async def update_after_download(event: asyncio.Event, lock: asyncio.Lock,
                                list_historic_instrument: list[HistoricInstrument], lock_list: asyncio.Lock):
    while True:
        await event.wait()
        print(f'Данные загрузились обновляем список ',
              ', '.join([f'{i.instrument_info.ticker}-{i.max_donchian}' for i in list_historic_instrument]),
              'старый список')
        async with lock_list:
            list_historic_instrument.clear()
        for folder in os.listdir(r'C:\Users\aples\PycharmProjects\Gas\trad'):
            if not os.path.isfile(os.path.join(r'C:\Users\aples\PycharmProjects\Gas\trad', folder)):
                if not folder.startswith('__'):
                    for file in os.listdir(os.path.join(r'C:\Users\aples\PycharmProjects\Gas\trad', folder)):
                        file = file.split('.')[0]
                        async with lock:
                            historic_instrument = HistoricInstrument(from_csv=True, path=os.path.join(
                                r'C:\Users\aples\PycharmProjects\Gas\trad', folder, file))
                        async with lock_list:
                            list_historic_instrument.append(historic_instrument)
                        break
        async with lock_list:
            for historic in list_historic_instrument:
                historic.create_donchian_canal(20, 10)
        print('Данные обновлены: ',
              ', '.join([f'{i.instrument_info.ticker}-{i.max_donchian}' for i in list_historic_instrument]), '\n')
        event.clear()


async def gen(connect: ConnectTinkoff):
    pass


async def function():
    lock = asyncio.Lock()
    lock_list = asyncio.Lock()
    event = asyncio.Event()
    connect = ConnectTinkoff(TOKEN)
    dict_instruments_time = {}
    list_historic_instrument = []
    await connect.connect()
    update_task = asyncio.create_task(update(connect, dict_instruments_time, event, lock))
    update_after_download_task = asyncio.create_task(
        update_after_download(event=event,
                              lock=lock,
                              list_historic_instrument=list_historic_instrument,
                              lock_list=lock_list))

    while not dict_instruments_time:
        print("Ожидание обновления данных...")
        await asyncio.sleep(5)
    subscribe_tasks = []
    for instrument_id in dict_instruments_time.keys():
        subscribe_tasks.append(connect.add_subscribe(instrument_id=instrument_id))
    await asyncio.gather(*subscribe_tasks)
    await asyncio.sleep(10)

    for folder in os.listdir(r'C:\Users\aples\PycharmProjects\Gas\trad'):
        if not os.path.isfile(os.path.join(r'C:\Users\aples\PycharmProjects\Gas\trad', folder)):
            if not folder.startswith('__'):
                for file in os.listdir(os.path.join(r'C:\Users\aples\PycharmProjects\Gas\trad', folder)):
                    file = file.split('.')[0]
                    async with lock:
                        historic_instrument = HistoricInstrument(from_csv=True, path=os.path.join(
                            r'C:\Users\aples\PycharmProjects\Gas\trad', folder, file))
                    list_historic_instrument.append(historic_instrument)
                    break

    for historic in list_historic_instrument:
        historic.create_donchian_canal(20, 10)

    while True:
        msg: MarketDataResponse = await connect.queue.get()
        print(msg)
        if msg is None:  # например, если используете None как сигнал завершения
            break
        if msg.candle is not None:
            async with lock_list:
                for historic_instrument in list_historic_instrument:
                    if historic_instrument.instrument_info.figi == msg.candle.figi:
                        print(f'Инструмент {historic_instrument.instrument_info.ticker}')
                        print(
                            f'Нынешний канал {historic_instrument.max_donchian}, Максимальная цена свечи: {quotation_to_decimal(msg.candle.high)}')
                        if quotation_to_decimal(msg.candle.high) > historic_instrument.max_donchian:
                            print(f'Пробитие канала.')

    await update_task
    await update_after_download_task
    await connect.disconnect()


if __name__ == '__main__':
    asyncio.run(function())
