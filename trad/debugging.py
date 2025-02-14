import datetime
import pickle
from decimal import Decimal
import pickle as pkl
import os

import pandas as pd
from tinkoff.invest import MarketDataResponse, PortfolioResponse
from tinkoff.invest.utils import quotation_to_decimal, money_to_decimal

from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from data_create.historic_future import HistoricInstrument
import asyncio
from config import TOKEN, TOKEN_D
from utils import market_data_response_to_string


async def main():
    connect = ConnectTinkoff(TOKEN_D)
    await connect.connect()
    result: list[PortfolioResponse] = await connect.info_accounts()
    print(result[0])
    for i in result:
        portfolio = ''
        for x in i.positions:
            portfolio += (f'Figi-идентификатора инструмента. {x.figi}\n'
                          f'Тип инструмента. {x.instrument_type}\n'
                          f'Количество инструмента в портфеле в штуках. {quotation_to_decimal(x.quantity)}\n'
                          f'Средневзвешенная цена позиции. {money_to_decimal(x.average_position_price)}\n'
                          f'Текущая рассчитанная доходность позиции. {quotation_to_decimal(x.expected_yield)}\n'
                          f'Текущий НКД. {money_to_decimal(x.current_nkd)}\n'
                          f'Deprecated Средняя цена позиции в пунктах (для фьючерсов) {quotation_to_decimal(x.average_position_price_pt)}\n'
                          f'Текущая цена за 1 инструмент. Для получения стоимости лота требуется умножить на лотность инструмента. {money_to_decimal(x.current_price)}\n'
                          f'Средняя цена позиции по методу FIFO. {money_to_decimal(x.average_position_price_fifo)}\n'
                          f'Deprecated Количество лотов в портфеле. {quotation_to_decimal(x.quantity_lots)}\n'
                          f'Заблокировано на бирже. {x.blocked}\n'
                          f'Количество бумаг, заблокированных выставленными заявками. {quotation_to_decimal(x.blocked_lots)}\n'
                          f'Вариационная маржа. {money_to_decimal(x.var_margin)}\n'
                          f'Текущая рассчитанная доходность позиции. {quotation_to_decimal(x.expected_yield_fifo)}\n\n')
        text = (f'ID: {i.account_id}\n'
                f'List position:\n{portfolio}'
                f'Total amount: {money_to_decimal(i.total_amount_portfolio)}')
        print(text)


if __name__ == '__main__':
    # Допустим, у нас есть данные для инструмента "BMH5"
    context = StrategyContext(
        history_instrument=HistoricInstrument.from_pkl(
            path=r'C:\Users\aples\PycharmProjects\Gas\IMOEXF Индекс МосБиржи\FUTIMOEXF000'),
        portfolio_size=100000,
        n=20  # размер портфеля, например, 100,000
    )

    dict_strategy_context = {
        f'{context.instrument_figi}': context
    }
    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'wb') as f:
        pickle.dump(dict_strategy_context, f, protocol=pickle.HIGHEST_PROTOCOL)
