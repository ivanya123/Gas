import asyncio
import pickle

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from bot.telegram_bot import bot
from data_create.historic_future import HistoricInstrument
from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from config import TOKEN, CHAT_ID, TOKEN_D
import utils as ut
import bot.keyboard as kb
from trad.task_all_time import conclusion_in_day

start_router = Router()
dict_function = {}
dict_instruments = {}
connect = ConnectTinkoff(TOKEN_D)
event_stop_stream_to_chat = asyncio.Event()


@start_router.message(F.text.startswith('Bot_subscribe'))
async def subscribe(message: Message):
    try:
        tickers = message.text.split(' ')[1:]
        # ut.validate_tickers(tickers)
    except IndexError as e:
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
            dict_strategy_subscribe[new_historic_instrument.instrument_info.figi] = (
                StrategyContext(new_historic_instrument, n=20, portfolio_size=220000))
            with open('dict_strategy_state.pkl', 'wb') as f:
                pickle.dump(dict_strategy_subscribe, f)
        await connect.add_subscribe_last_price(instruments)
        await connect.add_subscribe_status_instrument(instruments)
        list_task = [connect.figi_to_name(figi) for figi in figi_instruments]
        await asyncio.gather(*list_task)
        for instrument in his_instr:
            ut.create_folder_and_save_historic_instruments(instrument)
    else:
        await bot.send_message(chat_id=message.chat.id, text='Подключение не установлено')


@start_router.message(CommandStart())
async def start(message: Message):
    await bot.send_message(chat_id=message.chat.id,
                           text='При нажатии покажет информацию о позиции',
                           reply_markup=kb.kb_ticker())


@start_router.message(F.text == 'Bot_portfolio')
async def portfolio(message: Message):
    await conclusion_in_day(connect, bot)


@start_router.callback_query(F.data)
async def callback(callback: CallbackQuery):
    with open('dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_subscribe: dict[str, StrategyContext] = pickle.load(f)
    context: StrategyContext = dict_strategy_subscribe[callback.data]
    dict_info = context.current_position_info()
    text = '\n'.join(f'{key}: {value}' for key, value in dict_info.items())
    await bot.send_message(chat_id=callback.message.chat.id, text=text)


@start_router.message(Command('tasks'))
async def tasks(message: Message):
    tasks = asyncio.all_tasks()
    text = ''
    for task in tasks:
        text += f'{task}\n'
    await bot.send_message(chat_id=message.chat.id, text=text)

