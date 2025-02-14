import pickle

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from strategy.docnhian import StrategyContext


def kb_ticker():
    with open('dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
    list_buttons = [
        [InlineKeyboardButton(text=value.ticker, callback_data=key)] for key, value in dict_strategy_state.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=list_buttons)