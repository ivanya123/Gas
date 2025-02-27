import pickle
import shelve

# from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from strategy.docnhian import StrategyContext


def kb_ticker():
    with shelve.open('data_strategy_state/dict_strategy_state') as db:
        db: dict[str, StrategyContext]
        list_buttons = [
            [InlineKeyboardButton(text=value.history_instrument.instrument_info.name, callback_data=key)]
            for key, value in db.items()
        ]
        return InlineKeyboardMarkup(inline_keyboard=list_buttons)
