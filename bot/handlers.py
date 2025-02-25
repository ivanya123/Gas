import asyncio
import pickle

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from tinkoff.invest import GetMarginAttributesResponse, PortfolioResponse
from tinkoff.invest.utils import money_to_decimal

import bot.keyboard as kb
import utils as ut
from bot.telegram_bot import bot
from config import TOKEN_TEST, ACCOUNT_ID
from data_create.historic_future import HistoricInstrument
from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from trad.task_all_time import conclusion_in_day

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
        instruments = []
        figi_instruments = []
        his_instr: list[HistoricInstrument] = []
        for ticker in tickers:
            try:
                historic_instrument, instrument_info = await connect.get_candles_from_ticker(ticker=ticker,
                                                                                             interval='1h')
                new_historic_instrument = HistoricInstrument(instrument=instrument_info,
                                                             list_candles=historic_instrument)
            except Exception as e:
                await bot.send_message(chat_id=message.chat.id,
                                       text=f'Не удалось получить данные по тикеру {ticker}:\n{e}')
                continue
            his_instr.append(new_historic_instrument)
            instruments.append(new_historic_instrument.instrument_info.uid)
            figi_instruments.append(new_historic_instrument.instrument_info.figi)

            with open('dict_strategy_state.pkl', 'rb') as f:
                dict_strategy_subscribe: dict[str, StrategyContext] = pickle.load(f)
            my_portfolio: PortfolioResponse = await connect.get_portfolio_by_id(ACCOUNT_ID)
            dict_strategy_subscribe[new_historic_instrument.instrument_info.figi] = (
                StrategyContext(new_historic_instrument, n=20,
                                portfolio_size=money_to_decimal(my_portfolio.total_amount_portfolio))
            )
            with open('dict_strategy_state.pkl', 'wb') as f:
                pickle.dump(dict_strategy_subscribe, f)

        await connect.add_subscribe_last_price(instruments)
        await connect.add_subscribe_status_instrument(instruments)
        list_task = [connect.figi_to_name(figi) for figi in figi_instruments]
        await asyncio.gather(*list_task)
        for instrument in his_instr:
            ut.create_folder_and_save_historic_instruments(instrument)
        await bot.send_message(chat_id=message.chat.id, text='Подписка установлена')

    else:
        await bot.send_message(chat_id=message.chat.id, text='Подключение не установлено')


@start_router.message(CommandStart())
async def start(message: Message):
    result = await connect.client.users.get_accounts()
    print(result)
    await bot.send_message(chat_id=message.chat.id,
                           text='При нажатии покажет информацию о позиции',
                           reply_markup=kb.kb_ticker())


@start_router.message(F.text == 'Bot_portfolio')
async def portfolio():
    await conclusion_in_day(connect, bot)


@start_router.callback_query(F.data)
async def callback(call_back: CallbackQuery):
    with open('dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_subscribe: dict[str, StrategyContext] = pickle.load(f)
    context: StrategyContext = dict_strategy_subscribe[call_back.data]
    dict_info = context.current_position_info()
    text = '\n'.join(f'{key}: {value}' for key, value in dict_info.items())
    await bot.send_message(chat_id=call_back.message.chat.id, text=text)


@start_router.message(Command('tasks'))
async def tasks(message: Message):
    list_task: list[asyncio.Task] = asyncio.all_tasks()
    text = ''
    for task in list_task:
        text += f'{task.get_name()}\n'
    await bot.send_message(chat_id=message.chat.id, text=text, parse_mode=None)


@start_router.message(F.text == 'margin')
async def margin(message: Message):
    result: GetMarginAttributesResponse = await connect.client.users.get_margin_attributes(account_id=ACCOUNT_ID)
    test = '\n'.join(f'{key}: {value}' for key, value in result.__dict__.items())
    print(test)
    await bot.send_message(chat_id=message.chat.id, text=test, parse_mode=None)
