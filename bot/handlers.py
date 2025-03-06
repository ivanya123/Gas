import asyncio
import shelve
from decimal import Decimal

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from tinkoff.invest import GetMarginAttributesResponse

import bot.keyboard as kb
import utils as ut
from bot.telegram_bot import bot
from config import TOKEN_TEST, ACCOUNT_ID
from data_create.historic_future import HistoricInstrument
from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from trad.task_all_time import conclusion_in_day, get_context_by_figi

start_router = Router()
dict_function = {}
dict_instruments = {}
connect = ConnectTinkoff(TOKEN_TEST)
event_stop_stream_to_chat = asyncio.Event()


@start_router.message(F.text.startswith('Bot_subscribe'))
async def subscribe(message: Message):
    try:
        tickers = message.text.split(' ')[1:]
        # ut.validate_tickers(tickers)
    except IndexError:
        await bot.send_message(chat_id=message.chat.id, text='Неверный формат команды')
        return
    if connect.client:
        dict_historic = {}
        for ticker in tickers:
            try:
                historic_instrument, instrument_info = await connect.get_candles_from_ticker(ticker=ticker,
                                                                                             interval='1d')
                new_historic_instrument = HistoricInstrument(instrument=instrument_info,
                                                             list_candles=historic_instrument)
            except Exception as e:
                await bot.send_message(chat_id=message.chat.id,
                                       text=f'Не удалось получить данные по тикеру {ticker}:\n{e}')
                continue
            dict_historic[new_historic_instrument.instrument_info.figi] = new_historic_instrument
        with shelve.open('data_strategy_state/dict_strategy_state') as db:
            db: dict[str, StrategyContext]
            for figi in dict_historic:
                if figi in db.keys():
                    context = db[figi]
                    context.update_data(dict_historic[figi])
                    db[figi] = context
                else:
                    context = StrategyContext(dict_historic[figi])
                    db[figi] = context

        instruments = [instrument.instrument_info for instrument in dict_historic.values()]
        await connect.add_subscribe_last_price(instruments)
        await connect.add_subscribe_status_instrument(instruments)
        list_task = [connect.figi_to_name(figi) for figi in dict_historic]
        await asyncio.gather(*list_task)
        for instrument in dict_historic.values():
            ut.create_folder_and_save_historic_instruments(instrument)
        await bot.send_message(chat_id=message.chat.id, text='Подписка установлена')

    else:
        await bot.send_message(chat_id=message.chat.id, text='Подключение не установлено')


@start_router.message(CommandStart())
async def start(message: Message):
    await bot.send_message(chat_id=message.chat.id,
                           text='При нажатии покажет информацию о позиции',
                           reply_markup=kb.kb_ticker())


@start_router.message(F.text == 'Bot_portfolio')
async def portfolio():
    await conclusion_in_day(connect, bot)


@start_router.callback_query(F.data)
async def callback(call_back: CallbackQuery):
    context: StrategyContext = get_context_by_figi(call_back.data)
    dict_info = context.current_position_info()
    text = '\n'.join(
        f'{key}: {value:.2f}' if isinstance(value, (int, float, Decimal)) else f'{key}: {value}' for key, value in
        dict_info.items()
    )
    await bot.send_message(chat_id=call_back.message.chat.id, text=text)


@start_router.message(F.text == 'margin')
async def margin(message: Message):
    result: GetMarginAttributesResponse = await connect.client.users.get_margin_attributes(account_id=ACCOUNT_ID)
    test = '\n'.join(f'{key}: {value}' for key, value in result.__dict__.items())
    print(test)
    await bot.send_message(chat_id=message.chat.id, text=test, parse_mode=None)


@start_router.message(F.text == 'Bot_update_position')
async def update_position(message: Message):
    try:
        dict_state: dict[str, StrategyContext] = {}
        with shelve.open('data_strategy_state/dict_strategy_state') as db:
            for key in db.keys():
                context = db[key]
                dict_state[key] = context
        my_portfolio = await connect.get_portfolio_by_id(ACCOUNT_ID)
        portfolio_positions = {position.figi: position for position in my_portfolio.positions}

        for key, value in dict_state.items():
            if key in portfolio_positions:
                await value.update_position_info(connect, portfolio_positions[key])
            else:
                await value.update_position_info(connect, None)

        with shelve.open('data_strategy_state/dict_strategy_state') as db:
            for key in db.keys():
                db[key] = dict_state[key]
        await bot.send_message(chat_id=message.chat.id, text='Позиции обновлены')
    except Exception as e:
        await bot.send_message(chat_id=message.chat.id, text=f'Ошибка при обновлении позиций: {e}')


@start_router.message(Command('unsubscribe'))
async def unsubscribe(message: Message):
    await bot.send_message(chat_id=message.chat.id,
                           text='Выберите инструмент для отписки',
                           reply_markup=kb.kb_unsubscribe())


@start_router.callback_query(F.data)
async def unsubscribe_data(call_back: CallbackQuery):
    key = call_back.data.split('-')[0]
    with shelve.open('data_strategy_state/dict_strategy_state') as db:
        context: 'StrategyContext' = db[key]
        if context.quantity > 0:
            await bot.send_message(chat_id=call_back.message.chat.id, text=(f'Нельзя отписаться от позиции\n'
                                                                            f'{context.quantity} лотов держится'))
        else:
            del db[key]
            await connect.delete_subscribe(context.history_instrument.instrument_info.uid, last_price=True)
            await bot.send_message(chat_id=call_back.message.chat.id, text='Отписка от позиции успешно отменена')
