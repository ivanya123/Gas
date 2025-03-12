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

    # with shelve.open('data_strategy_state/dict_strategy_state') as db:
    #     db: dict[str, 'StrategyContext']
    #     context = db['FUTNGM032500']
    #     print(context.entry_prices)
    #     print(context.stop_levels)
    #     print(context.quantity)
    a = int(Decimal(12.0))
    print(a)







