import asyncio
import datetime
import os
import pickle
import shelve

from tinkoff.invest import FutureResponse, AsyncClient, PositionsResponse, OperationsResponse, OperationType, \
    GetOperationsByCursorResponse, GetOperationsByCursorRequest
from tinkoff.invest.utils import now

from config import TOKEN_D, ACCOUNT_ID, TOKEN_TEST
from data_create.historic_future import HistoricInstrument
from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff

if __name__ == '__main__':

    async def main():
        connect = ConnectTinkoff(TOKEN_TEST)
        await connect.connection()
        with shelve.open('data_strategy_state/dict_strategy_state') as db:
            for key in db.keys():
                values: StrategyContext = db[key]
                candles, instrument_info = await connect.get_candles_from_uid(
                    uid=values.history_instrument.instrument_info.uid,
                    interval='1d'
                )
                new_history = HistoricInstrument(list_candles=candles, instrument=instrument_info)
                db[key] = StrategyContext(new_history)


    async def main_1():
        connect = ConnectTinkoff(TOKEN_TEST)
        await connect.connection()
        portfolio = await connect.get_portfolio_by_id(ACCOUNT_ID)
        portfolio_positions = {position.figi: position for position in portfolio.positions}
        # print('\n'.join(f'{key}: {val}' for key, val in portfolio_positions['FUTNGM052500'].__dict__.items()))
        with shelve.open('data_strategy_state/dict_strategy_state') as db:
            for key in db.keys():
                if key in portfolio_positions:
                    print(key)
                    values: StrategyContext = db[key]
                    print(values.current_position_info())
                    await values.update_position_info(connect=connect, portfolio=portfolio_positions[key])
                    print(values.current_position_info())
                    db[key] = values


    asyncio.run(main_1())
