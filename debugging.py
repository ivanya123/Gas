import asyncio
import datetime
import os
import pickle
import shelve
from decimal import Decimal

from tinkoff.invest import FutureResponse, AsyncClient, PositionsResponse, OperationsResponse, OperationType, \
    GetOperationsByCursorResponse, GetOperationsByCursorRequest
from tinkoff.invest.utils import now, money_to_decimal, quotation_to_decimal

from config import TOKEN_D, ACCOUNT_ID, TOKEN_TEST
from data_create.historic_future import HistoricInstrument
from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff

if __name__ == '__main__':

    with shelve.open(r'C:\Users\aples\PycharmProjects\Gas\data_strategy_state\dict_strategy_state') as db:
        for key in db:
            fake_context: StrategyContext = db[key]
            break

    print(fake_context.history_instrument.instrument_info.name)
    print(fake_context.breakout_level_long)
    print(fake_context.breakout_level_short)






