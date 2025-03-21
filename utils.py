"""
Функции для обработки ответов от Tinkoff API и преобразование их в другой формат.
"""
from __future__ import annotations

import json
import logging
import math
import os
import uuid
from decimal import Decimal
from functools import lru_cache
from zoneinfo import ZoneInfo

from tinkoff.invest import MarketDataResponse, PortfolioStreamResponse, PositionsStreamResponse, \
    TradesStreamResponse, OrderDirection
from tinkoff.invest.utils import quotation_to_decimal, money_to_decimal

from data_create.historic_future import HistoricInstrument

logger = logging.getLogger(__name__)


def market_data_response_to_string(msg: MarketDataResponse) -> str:
    """
    Преобразует ответ от API в строку.
    :param msg: Ответ от API.
    :return: Строка с данными.
    """
    string = ''
    if msg.subscribe_candles_response:
        candle_sub = msg.subscribe_candles_response.candles_subscriptions
        string_sub = ''
        for sub in candle_sub:
            string_sub += (f'Name: {figi_to_name(sub.figi)}\n'
                           f'Interval: {sub.interval.name}\n\n')
        string += f'Оформлены подписки:\n{string_sub}\n'

    if msg.subscribe_order_book_response:
        order_book_sub = msg.subscribe_order_book_response.order_book_subscriptions
        string_sub = ''
        for sub in order_book_sub:
            string_sub += (f'Name: {figi_to_name(sub.figi)}\n'
                           f'Depth: {sub.depth}\n\n')
        string += f'Оформлены подписки на стаканы:\n{string_sub}\n'

    if msg.subscribe_last_price_response:
        last_price_sub = msg.subscribe_last_price_response.last_price_subscriptions
        string_sub = ''
        for sub in last_price_sub:
            string_sub += f'Name: {figi_to_name(sub.figi)}\n'
        string += f'Оформлены подписки на последние цены:\n{string_sub}\n'

    if msg.candle:
        candle = msg.candle
        dt_moscow = candle.time.astimezone(ZoneInfo("Europe/Moscow"))
        string += f'Получена свеча:\n'
        string += (f'Name: {figi_to_name(candle.figi)}\n'
                   f'Interval: {candle.interval.name}\n'
                   f'Open: {quotation_to_decimal(candle.open)}\n'
                   f'Close: {quotation_to_decimal(candle.close)}\n'
                   f'High: {quotation_to_decimal(candle.high)}\n'
                   f'Low: {quotation_to_decimal(candle.low)}\n'
                   f'Volume: {candle.volume}\n'
                   f'Time: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n')

    if msg.orderbook:
        orderbook = msg.orderbook
        string += f'Получен стакан:\n'
        dt_moscow = orderbook.time.astimezone(ZoneInfo("Europe/Moscow"))
        string += (f'Name: {figi_to_name(orderbook.figi)}\n'
                   f'Depth: {orderbook.depth}\n'
                   f'Time: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n')
        bids_sum = sum([quotation_to_decimal(order.price) * order.quantity for order in orderbook.bids])
        asks_sum = sum([quotation_to_decimal(order.price) * order.quantity for order in orderbook.asks])
        string += f'Сумма заявок на покупку: {bids_sum}\n'
        string += f'Сумма заявок на продажу: {asks_sum}\n'
        string += f'Сумма заявок: {bids_sum + asks_sum}\n'
        string += f'Верхний лимит цены за 1 инструмент: {quotation_to_decimal(orderbook.limit_up)}\n'
        string += f'Нижний лимит цены за 1 инструмент: {quotation_to_decimal(orderbook.limit_down)}\n'

    if msg.last_price:
        last_price = msg.last_price
        dt_moscow = last_price.time.astimezone(ZoneInfo("Europe/Moscow"))
        string += f'Получена последняя цена:\n'
        string += (f'Name: {figi_to_name(last_price.figi)}\n'
                   f'Price: {quotation_to_decimal(last_price.price)}\n'
                   f'Time: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n')

    if msg.subscribe_info_response:
        info_sub = msg.subscribe_info_response.info_subscriptions
        string_sub = ''
        for sub in info_sub:
            string_sub += f'Name: {figi_to_name(sub.figi)}\n'
        string += f'Оформлены подписки на информацию о торговых инструментах:\n{string_sub}\n'

    if msg.trading_status:
        status = msg.trading_status
        dt_moscow = status.time.astimezone(ZoneInfo("Europe/Moscow"))
        string += (f'Изменен статус торгов <b>{figi_to_name(status.figi)}</b>\n'
                   f'Доступность выставления лимитной заявки: {status.limit_order_available_flag}\n'
                   f'Доступность выставления рыночной заявки: {status.market_order_available_flag}\n'
                   f'Time: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n')

    if msg.ping:
        string += f'Получен пинг:\n'
        string += f'Time: {msg.ping.time.strftime("%Y-%m-%d %H:%M:%S")}\n'

    return string


def create_folder_and_save_historic_instruments(historic_instruments: HistoricInstrument):
    """
    Создаёт папку с историческими данными и сохраняет в нее данныe.
    :param historic_instruments: Данные для сохранения.
    """
    if not os.path.exists('my_data_folder'):
        os.mkdir('my_data_folder')
    src = os.path.join('my_data_folder', historic_instruments.instrument_info.name)
    if not os.path.exists(src):
        os.mkdir(src)
    path = os.path.join('my_data_folder', historic_instruments.instrument_info.name,
                        historic_instruments.instrument_info.figi)
    historic_instruments.create_donchian_canal(20, 10)
    historic_instruments.save_to_csv(
        path=path,
        index=False
    )
    return path


def new_save_subs(dict_subs):
    with open('subscribe.json', 'r') as file:
        subs = json.load(file)
    with open('subscribe.json', 'w') as file:
        subs.update(dict_subs)
        json.dump(subs, file)


def get_all_path_subs(dict_instruments: dict[str, list[str]]) -> tuple[list[str]]:
    """
    Получает пути к папкам с данными фьючерсов, на которые подписаны в данный момент.
    Словарь выглядит таким образом {figi: [uid, name, ticker], …}
    :param dict_instruments: Словарь с инструментами.
    :return: Словарь с подписками.
    """
    list_path_true = []
    keys_false = []
    for key, value in dict_instruments.items():
        name = value[1]
        if os.path.exists(name):
            if key in os.listdir(name)[0]:
                path = os.listdir(name)[0].split('.')[0]
                full_path = os.path.join(name, path)
                list_path_true.append(full_path)
        else:
            keys_false.append(key)
    return list_path_true


def psr_to_string(psr: PortfolioStreamResponse) -> str:
    string = ''
    portfolio_size = None
    if portfolio := psr.portfolio:
        for position in portfolio.positions:
            string += (f'{figi_to_name(position.figi)}-{position.instrument_type}\n'
                       f'Доходность: '
                       f'{position.expected_yield:.2f}-({(quotation_to_decimal(position.expected_yield) /
                                                          (quotation_to_decimal(position.quantity) *
                                                           money_to_decimal(position.average_position_price))):.1%})\n')
        string += (f'\nОбщая информация по портфелю\n'
                   f'Доходность: {portfolio.expected_yield}%\n'
                   f'Стоимость портфеля: {money_to_decimal(portfolio.total_amount_portfolio)}')
        portfolio_size = money_to_decimal(portfolio.total_amount_portfolio)

    if psr.ping:
        dt_moscow = psr.ping.time.astimezone(ZoneInfo("Europe/Moscow"))
        string += f'Получен пинг:\n' \
                  f'Time: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n'

    if psr.subscriptions:
        string += 'Оформлена подписка на стрим портфолио'

    return string, portfolio_size


def position_to_string(position: PositionsStreamResponse) -> str:
    string = ''
    if position.subscriptions:
        string += 'Оформлена подписка на стрим позиций'

    if pos := position.position:
        if futures := pos.futures:
            for fut in futures:
                string += (f'Изменение позиции по фьючерсу {figi_to_name(fut.figi)}\n'
                           f'Количество бумаг заблокированных выставленными заявками: {fut.blocked}\n'
                           f'Текущий не заблокированный баланс: {fut.balance}\n')
        dt_moscow = pos.date.astimezone(ZoneInfo("Europe/Moscow"))
        string += f'Дата: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n'

        if money := pos.money:
            for m in money:
                string += (f'Изменение позиции по валютной позиции\n'
                           f'Доступное количество валютный позиций '
                           f'{money_to_decimal(m.available_value):.2f} '
                           f'{m.available_value.currency}\n'
                           f'Заблокированное количество валютный позиций: '
                           f'{money_to_decimal(m.blocked_value):.2f} '
                           f'{m.blocked_value.currency}')
        if position.ping:
            dt_moscow = position.ping.time.astimezone(ZoneInfo("Europe/Moscow"))
            string += f'Получен пинг:\n' \
                      f'Time: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n'
    return string


@lru_cache
def figi_to_name(figi: str) -> str:
    with open('figi_to_name.json', 'r') as f:
        name_dict: dict[str, str] = json.load(f)
    return name_dict[figi]


def calculation_quantity(price_rub_one_point: Decimal, portfolio: Decimal, atr: Decimal) -> int:
    """
    Вычисляет количество бумаг для покупки.
    :param price_rub_one_point: Цена покупки.
    :param portfolio: Размер моего счёта.
    :param atr: Средний истинный диапазон за 14 дней.
    :return: Количество лотов для выставления ордера.
    """
    quantity = math.floor(Decimal(0.01) * portfolio / (atr * price_rub_one_point))
    if quantity == 0:
        raise Exception(f'Кол-во лотов для сделки равно 0')
    return quantity


def generate_order_id():
    return str(uuid.uuid4())


def tsr_to_string(trades_stream_response: TradesStreamResponse):
    text = ''
    if trades := trades_stream_response.order_trades:
        dt_moscow = trades_stream_response.order_trades.created_at.astimezone(ZoneInfo("Europe/Moscow"))
        text += (f'Информация об исполнении торгового поручения\n'
                 f'<b>{figi_to_name(trades.figi)}</b>\n'
                 f'Время создания: {dt_moscow.strftime("%Y-%m-%d %H:%M:%S")}\n'
                 f"Направление: {'Лонг' if trades.direction == OrderDirection.ORDER_DIRECTION_BUY else 'Шорт'}\n\n")
        for trade in trades.trades:
            text += (f'Цена: {money_to_decimal(trade.price):.2f}\n'
                     f'Количество: {trade.quantity}\n')
    if trades_stream_response.ping:
        text += f'Пинг: {trades_stream_response.ping}\n'
    return text
