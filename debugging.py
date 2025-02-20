import asyncio
import datetime
import json
import os
import pickle

from tinkoff.invest import MarketDataResponse

from bot.telegram_bot import logger
from config import TOKEN_D
from data_create.historic_future import HistoricInstrument
from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from trad.task_all_time import processing_stream_portfolio
import utils as ut


async def main():
    connect = ConnectTinkoff(TOKEN_D)
    await connect.connect()
    time = datetime.datetime.now()
    k = await connect.figi_to_name('FUTIMOEXF000')
    print('1:', datetime.datetime.now() - time, k, sep=' ')

    time = datetime.datetime.now()
    k = await connect.figi_to_name('FUTIMOEXF000')
    print('2:', datetime.datetime.now() - time, k, sep=' ')


def m():
    with open('dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
    with open('figi_to_name.json', 'w') as f:
        dict_name = {v.instrument_figi: v.name for v in dict_strategy_state.values()}
        json.dump(dict_name, f, indent=4)


if __name__ == '__main__':
    async def main():
        # dict_startegy_state = {}
        # for folder, foldrs, files in os.walk(r'C:\Users\aples\PycharmProjects\Gas'):
        #     if (r'C:\Users\aples\PycharmProjects\Gas\.venv' not in folder
        #             and r'C:\Users\aples\PycharmProjects\Gas\.git' not in folder
        #             and r'C:\Users\aples\PycharmProjects\Gas\bot' not in folder
        #             and r'C:\Users\aples\PycharmProjects\Gas\config' not in folder
        #             and r'C:\Users\aples\PycharmProjects\Gas\pip' not in folder
        #             and '__pycache__' not in folder
        #             and '.idea' not in folder):
        #         if files[0].endswith('.csv'):
        #             path = os.path.join(folder, files[0]).replace('.csv', '')
        #             history: HistoricInstrument = HistoricInstrument.from_pkl(path)
        #             dict_startegy_state[history.instrument_info.figi] = StrategyContext(history, 200000, 20)
        # with open('dict_strategy_state.pkl', 'wb') as f:
        #     pickle.dump(dict_startegy_state, f)
        connect = ConnectTinkoff(TOKEN_D)
        await connect.connect()

        with open('dict_strategy_state.pkl', 'rb') as f:
            dict_strategy_subscribe: dict[str, 'StrategyContext'] = pickle.load(f)
        instruments_id = [value.instrument_uid for value in dict_strategy_subscribe.values()]
        await connect.add_subscribe_last_price(instruments_id)
        list_msg = []
        task_l = asyncio.create_task(listen(connect, list_msg))
        await asyncio.sleep(240)
        task_l.cancel()
        try:
            await task_l
        except asyncio.CancelledError:
            logger.info('Получение сообщений отменено')

        logger.info(f'Список сообщений {list_msg}')
        with open(r'tests\list_msg_3.pkl', 'wb') as f:
            pickle.dump(list_msg, f)


    async def listen(connect, list_msg):
        while True:
            msg: MarketDataResponse = await connect.queue.get()
            list_msg.append(msg)
            logger.info(f'Положен в список {ut.market_data_response_to_string(msg)}')


    # def m():
    #     with open(r'C:\Users\aples\PycharmProjects\Gas\tests\list_msg.pkl', 'rb') as f:
    #         list_msg = pickle.load(f)
    #     for msg in list_msg:
    #         print(msg)
    #
    # m()
    asyncio.run(main())
