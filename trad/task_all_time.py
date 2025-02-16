import asyncio

import pickle

from aiogram import Bot
from tinkoff.invest import MarketDataResponse, PortfolioStreamResponse, PositionsStreamResponse
from tinkoff.invest.utils import quotation_to_decimal, money_to_decimal

from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from data_create.historic_future import HistoricInstrument
from config import CHAT_ID, ACCOUNT_ID, TOKEN_D
import utils as ut

event_stop_stream_to_chat = asyncio.Event()
event_update = asyncio.Event()


async def start_bot(connect: ConnectTinkoff, bot: Bot):
    await connect.connect()
    await bot.send_message(chat_id=CHAT_ID, text='Подключение установлено')
    with open('dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_subscribe: dict[str, StrategyContext] = pickle.load(f)
    instruments_id = [value.instrument_uid for value in dict_strategy_subscribe.values()]
    await update_data(connect, bot)
    await connect.add_subscribe_last_price(instruments_id)
    await connect.add_subscribe_status_instrument(instruments_id)


async def processing_stream(connect: ConnectTinkoff, bot: Bot):
    if connect.market_data_stream:
        while True:
            msg: MarketDataResponse = await connect.queue.get()
            with open('log.txt', 'a') as f:
                f.write(ut.market_data_response_to_string(msg) + '\n')
            if last_price := msg.last_price:
                try:
                    with open('dict_strategy_state.pkl', 'rb') as f:
                        dict_strategy_subscribe: dict[str, StrategyContext] = pickle.load(f)
                    if dict_strategy_subscribe[msg.last_price.figi]:
                        result = ut.processing_last_price(last_price, dict_strategy_subscribe[msg.last_price.figi])
                        if result:
                            with open('dict_strategy_state.pkl', 'wb') as f:
                                pickle.dump(dict_strategy_subscribe, f, pickle.HIGHEST_PROTOCOL)
                            await bot.send_message(chat_id=CHAT_ID, text=result)
                except Exception as e:
                    print(f"Произошла ошибка {e}")
            if msg.trading_status:
                msg_str = ut.market_data_response_to_string(msg) + '\n'
                await bot.send_message(chat_id=CHAT_ID, text=msg_str)
            if msg.subscribe_info_response or msg.subscribe_last_price_response:
                msg_str = ut.market_data_response_to_string(msg) + '\n'
                await bot.send_message(chat_id=CHAT_ID, text=msg_str)


async def processing_stream_portfolio(connect: ConnectTinkoff, bot: Bot):
    if connect.client:
        task_portfolio_stream = asyncio.create_task(connect.listening_portfolio_by_id(ACCOUNT_ID))
        task_operations_stream = asyncio.create_task(connect.listening_operations_by_id(ACCOUNT_ID))
        while not connect.queue_portfolio:
            await asyncio.sleep(4)
            print('Ждем подключения к стриму')
        while True:
            response: PortfolioStreamResponse | PositionsStreamResponse = await connect.queue_portfolio.get()
            if isinstance(response, PortfolioStreamResponse):
                text = ut.psr_to_string(response)
                await bot.send_message(chat_id=CHAT_ID, text=text)
            if isinstance(response, PositionsStreamResponse):
                text = ut.posr_to_string(response)
                await bot.send_message(CHAT_ID, text)


async def update_data(connect: ConnectTinkoff, bot: Bot):
    with open('dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
    text = ''
    for figi, context_strategy in dict_strategy_state.items():
        historic, info = await connect.get_candles_from_uid(uid=context_strategy.instrument_uid, interval='1d')
        new_historic = HistoricInstrument(instrument=info, list_candles=historic)
        new_historic.create_donchian_canal(context_strategy.n, int(context_strategy.n / 2))
        path = ut.create_folder_and_save_historic_instruments(new_historic)
        dict_strategy_state[figi].update_atr(new_historic)
        text += f'Данные для <b>{new_historic.instrument_info.name}</b> обновлены и сохранены в {path}\n\n'
    with open('dict_strategy_state.pkl', 'wb') as f:
        pickle.dump(dict_strategy_state, f)
    if text:
        await bot.send_message(chat_id=CHAT_ID, text=text)
    else:
        await bot.send_message(chat_id=CHAT_ID, text='Нет действующих подписок')


async def conclusion_in_day(connect: ConnectTinkoff, bot: Bot):
    if connect.client:
        with_draw, portfolio = await asyncio.gather(
            connect.client.operations.get_withdraw_limits(account_id=ACCOUNT_ID),
            connect.client.operations.get_portfolio(account_id=ACCOUNT_ID)
        )
        string = '<b>Данные по позициям</b>\n'
        if positions := portfolio.positions:
            for pos in positions:
                string += (f'<b>{await connect.figi_to_name(pos.figi)}-{pos.instrument_type}</b>\n'
                           f'Количество инструмента: {quotation_to_decimal(pos.quantity)}\n'
                           f'Средневзвешенная цена позиции: {quotation_to_decimal(pos.average_position_price):.2f}\n'
                           f'Текущая стоимость позиции: {quotation_to_decimal(pos.quantity) *
                                                         money_to_decimal(pos.current_price):.2f}\n'
                           f'Текущая рассчитанная доходность позиции: {quotation_to_decimal(pos.expected_yield):.2f}\n\n')

        string += (f'<b>Общая информация по портфелю</b>\n'
                   f'Доходность портфеля: <b>{quotation_to_decimal(portfolio.expected_yield):.2f}%</b>\n'
                   f'Общая стоимость портфеля: <b>{money_to_decimal(portfolio.total_amount_portfolio):.2f}</b>\n')

        text = ''
        text += (f'Массив валютных позиций портфеля:'
                 f' {sum(money_to_decimal(i) for i in with_draw.money):.2f}\n'
                 f'Массив заблокированных валютных позиций портфеля:'
                 f' {sum(money_to_decimal(i) for i in with_draw.blocked):.2f}\n'
                 f'Заблокировано под гарантийное обеспечение фьючерсов:'
                 f' <b>{sum(money_to_decimal(i) for i in with_draw.blocked_guarantee):.2f}</b>\n')

        await bot.send_message(chat_id=CHAT_ID, text=string)
        await bot.send_message(chat_id=CHAT_ID, text=text)


if __name__ == '__main__':
    async def main():
        connect = ConnectTinkoff(TOKEN_D)
        await connect.connect()
        await conclusion_in_day(connect, 1)


    asyncio.run(main())
