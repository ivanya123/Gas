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

    with open('logs.log', 'r') as f:
        for line in f.readlines():
            if 'Ошибка при получении сообщения:' in line:
                print(line)







