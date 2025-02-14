import asyncio
import pickle

from aiogram import Bot
from tinkoff.invest import MarketDataResponse, LastPrice, PortfolioStreamResponse, PositionsStreamResponse
from tinkoff.invest.utils import quotation_to_decimal

from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from data_create.historic_future import HistoricInstrument
from config import CHAT_ID, ACCOUNT_ID
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
            print(msg)
            print(ut.market_data_response_to_string(msg))
            with open('log.txt', 'a') as f:
                f.write(ut.market_data_response_to_string(msg) + '\n')
            if last_price := msg.last_price:
                try:
                    with open('dict_strategy_state.pkl', 'rb') as f:
                        dict_strategy_subscribe: dict[str, StrategyContext] = pickle.load(f)
                    if dict_strategy_subscribe[msg.last_price.figi]:
                        text = ut.processing_last_price(last_price, dict_strategy_subscribe[msg.last_price.figi])
                        print(dict_strategy_subscribe[msg.last_price.figi].state)
                        if text:
                            with open('dict_strategy_state.pkl', 'wb') as f:
                                pickle.dump(dict_strategy_subscribe, f, pickle.HIGHEST_PROTOCOL)
                            await bot.send_message(chat_id=CHAT_ID, text=text)
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
        while True:
            response: PortfolioStreamResponse | PositionsStreamResponse = await connect.queue_portfolio.get()
            if isinstance(response, PortfolioStreamResponse):
                psr_text = psr_to_string(response)








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
        text += f'Данные для {new_historic.instrument_info.name} обновлены и сохранены в {path}\n'
    with open('dict_strategy_state.pkl', 'wb') as f:
        pickle.dump(dict_strategy_state, f)
    if text:
        await bot.send_message(chat_id=CHAT_ID, text=text)
    else:
        await bot.send_message(chat_id=CHAT_ID, text='Нет действующих подписок')
