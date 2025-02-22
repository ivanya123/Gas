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
    await connect.connection()
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
    with open('dict_strategy_state.pkl', 'wb') as f:
        dict_strategy_state = {}
        pickle.dump(dict_strategy_state, f)

