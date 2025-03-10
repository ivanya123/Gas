from __future__ import annotations

import asyncio
import logging
import shelve
from decimal import Decimal
from typing import Optional
from typing import TYPE_CHECKING

from aiogram import Bot
from tinkoff.invest import MarketDataResponse, PortfolioStreamResponse, PositionsStreamResponse, TradesStreamResponse, \
    OrderState, OrderDirection, OrderType, OrderExecutionReportStatus, GetFuturesMarginResponse, \
    PostOrderResponse, LastPrice, Quotation, PriceType
from tinkoff.invest.utils import quotation_to_decimal, money_to_decimal, decimal_to_quotation

import utils as ut
from config import CHAT_ID, ACCOUNT_ID
from data_create.historic_future import HistoricInstrument
from trad.connect_tinkoff import ConnectTinkoff

if TYPE_CHECKING:
    from strategy.docnhian import StrategyContext

dict_status_instrument = {}
global_info_dict = {}
logger = logging.getLogger(__name__)


async def start_bot(connect: ConnectTinkoff, bot: Bot):
    await connect.connection()
    await bot.send_message(chat_id=CHAT_ID, text='Подключение установлено')
    with shelve.open('data_strategy_state/dict_strategy_state') as db:
        db: dict[str, 'StrategyContext']
        instruments_id = [value.history_instrument.instrument_info.uid for value in db.values()]
        figis = [value.history_instrument.instrument_info.figi for value in db.values()]

    await update_data(connect, bot)
    portfolio = await connect.get_portfolio_by_id(ACCOUNT_ID)
    list_corutin = [connect.figi_to_name(figi) for figi in figis]
    await asyncio.gather(*list_corutin)
    global_info_dict['portfolio_size'] = money_to_decimal(portfolio.total_amount_portfolio)
    await connect.add_subscribe_last_price(instruments_id)
    await connect.add_subscribe_status_instrument(instruments_id)


update_tasks: dict[str, asyncio.Task] = {}
dict_last_price: dict[str, Quotation] = {}


async def processing_stream(connect: ConnectTinkoff, bot: Bot) -> None:
    """
    Обработка потока данных котировок.
    :param connect: Класс для работы с Tinkoff API.
    :param bot: Телеграм бот.
    :return:
    """
    if connect.market_data_stream:
        while True:
            try:
                msg: MarketDataResponse = await connect.queue.get()
                logger.info(f'{ut.market_data_response_to_string(msg)}')
                if last_price := msg.last_price:  # если есть последняя цена
                    instrument_figi = last_price.figi
                    current_task = update_tasks.get(instrument_figi)
                    if current_task and not current_task.done():  # если задача обновления статуса уже запущена.
                        logger.debug(f'{instrument_figi} задача уже запущена')
                        # Кладем последний цену в словарь обновления,
                        # для возможности управления выставлением ордера в зависимости от новой цены инструмента.
                        dict_last_price[instrument_figi] = last_price.price
                        logger.debug(f'{dict_last_price} словарь обновлен')
                    else:  # если задача еще не запущена
                        # Запускаем задачу обновления
                        task = asyncio.create_task(update_strategy_by_price(last_price, connect, bot))
                        update_tasks[instrument_figi] = task  # Добавляем задачу в словарь
                        # Создаем callback, который удаляет задачу из словаря при завершении задачи.
                        task.add_done_callback(lambda t, key=instrument_figi: update_tasks.pop(key))

                if msg.trading_status:
                    msg_str = ut.market_data_response_to_string(msg) + '\n'
                    dict_status_instrument[msg.trading_status.instrument_uid] = msg.trading_status.trading_status
                    await bot.send_message(chat_id=CHAT_ID, text=msg_str)

                if msg.subscribe_info_response or msg.subscribe_last_price_response:
                    msg_str = ut.market_data_response_to_string(msg) + '\n'
                    await bot.send_message(chat_id=CHAT_ID, text=msg_str)
            except Exception as e:
                logger.exception(f'В функции обработки стрима произошла ошибка: {e}')


async def update_strategy_by_price(last_price: LastPrice, connect: ConnectTinkoff, bot: Bot):
    strategy_context = get_context_by_figi(last_price.figi)
    if strategy_context:
        result = await processing_last_price(last_price,
                                             strategy_context,
                                             connect)
        if result:
            save_context_by_figi(last_price.figi, strategy_context)
            await bot.send_message(chat_id=CHAT_ID, text=result)


def save_context_by_figi(figi: str, strategy_context: 'StrategyContext'):
    with shelve.open('data_strategy_state/dict_strategy_state') as db:
        db[figi] = strategy_context


def get_context_by_figi(figi: str) -> Optional['StrategyContext']:
    try:
        with shelve.open('data_strategy_state/dict_strategy_state') as db:
            strategy_context: 'StrategyContext' = db[figi]
        return strategy_context
    except KeyError:
        logger.error(f'Не удалось найти стратегию по figi: {figi}')
        return


async def processing_last_price(last_price: LastPrice,
                                context: 'StrategyContext',
                                connect: ConnectTinkoff
                                ):
    """
    Обрабатывает последнюю цену, полученную в стриме.
    :param connect: Класс подключения к TinkoffInvestApi.
    :param last_price: Цена последней сделки.
    :param context: Стадия отслеживаемого инструмента.
    :return:
    """
    price = quotation_to_decimal(last_price.price)
    result = await context.on_new_price(price, connect)
    if result:
        text = (f'Смена состояния подписки на {context.state.__class__.__name__}\n'
                f"{'\n'.join(f'{key}: {value}' for key, value in context.current_position_info().items())}")
        return text


async def processing_stream_portfolio(connect: ConnectTinkoff, bot: Bot):
    while True:
        response: PortfolioStreamResponse | PositionsStreamResponse = await connect.queue_portfolio.get()
        if isinstance(response, PortfolioStreamResponse):
            text, portfolio_amount = ut.psr_to_string(response)
            if not response.ping:
                await bot.send_message(chat_id=CHAT_ID, text=text)
            if portfolio_amount:
                global_info_dict['portfolio_size'] = portfolio_amount
        if isinstance(response, PositionsStreamResponse):
            text = ut.position_to_string(response)
            if not response.ping:
                await bot.send_message(CHAT_ID, text)


async def update_data(connect: ConnectTinkoff, bot: Bot):
    with shelve.open('data_strategy_state/dict_strategy_state') as db:
        db: dict[str, 'StrategyContext']
        text = ''
        for figi, context_strategy in db.items():
            historic, info = await connect.get_candles_from_uid(
                uid=context_strategy.history_instrument.instrument_info.uid,
                interval='1d'
            )
            new_historic = HistoricInstrument(instrument=info, list_candles=historic)
            path = ut.create_folder_and_save_historic_instruments(new_historic)
            context_strategy.update_data(new_historic)
            db[figi] = context_strategy
            text += f'Данные для <b>{new_historic.instrument_info.name}</b> обновлены и сохранены в {path}\n\n'

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
                           f'Текущая рассчитанная доходность позиции:'
                           f' {quotation_to_decimal(pos.expected_yield):.2f}\n\n')

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


dict_queue: dict[str, asyncio.Queue] = {}


async def processing_trades_stream(connect: ConnectTinkoff, bot: Bot):
    """
    Обрабатывает стрим ордеров.
    :param connect: Класс соединения с api Tinkoff
    :param bot: Телеграмм бот
    :return:
    """
    while True:
        trades_stream_response: TradesStreamResponse = await connect.queue_order.get()
        if order_trades := trades_stream_response.order_trades:
            if order_trades.figi not in dict_queue:
                logger.debug(f'Создана очередь для {order_trades.figi}')
                dict_queue[order_trades.figi] = asyncio.Queue()
            dict_queue[order_trades.figi].put_nowait(order_trades)
            await bot.send_message(chat_id=CHAT_ID, text=ut.tsr_to_string(trades_stream_response))


def compare_price(new_price: Quotation, order_state: OrderState, atr: Decimal, context: 'StrategyContext') -> bool:
    min_increment_amount = quotation_to_decimal(
        context.history_instrument.instrument_info.min_price_increment_amount)
    min_increment = quotation_to_decimal(context.history_instrument.instrument_info.min_price_increment)
    last_price = money_to_decimal(order_state.initial_order_price)
    last_price = ((last_price / min_increment_amount) * min_increment).quantize(Decimal('1.00'),
                                                                                rounding='ROUND_HALF_EVEN')
    logger.info(f'Цена последней выполненной сделки: {new_price}')
    logger.info(f'Цена по которой будет изменена заявка: {last_price + (atr / Decimal(2)):.2f}')
    direction = order_state.direction
    new_price = quotation_to_decimal(new_price)
    if direction == OrderDirection.ORDER_DIRECTION_BUY:
        return new_price >= (last_price + (atr / Decimal(2)))
    else:
        return new_price <= (last_price - (atr / Decimal(2)))


async def place_order_with_status_check(connect: ConnectTinkoff,
                                        context: 'StrategyContext',
                                        price: Decimal,
                                        long: bool,
                                        count: int = 500,
                                        retry_interval: int = 30
                                        ) -> Optional[list[OrderState]]:
    """
    Выставляет ордер и ждёт его подтверждения.
    :param connect: объект подключения (например, ConnectTinkoff)
    :param context: объект StrategyContext для текущего инструмента.
    :param price: Цена, по которой выставляется ордер.
    :param long: Направление ордера (True - лонг, False - шорт).
    :param count: Кол-во попыток подтверждения ордера.
    :param retry_interval: Интервал между повторными попытками (в секундах)
    :return: статус ордера или ошибка, если ордер отменён/не принят.
    """
    order_id = ut.generate_order_id()
    if 'portfolio_size' in global_info_dict:
        portfolio_size = global_info_dict['portfolio_size']
    else:
        portfolio_size = await connect.get_portfolio_by_id(ACCOUNT_ID)
        portfolio_size = money_to_decimal(portfolio_size.total_amount_portfolio)

    price_rub_point, price_in_rub, min_price_increment = await get_rub_price(connect, context, price)
    # Гарантирует что, цена будет кратна минимальному шагу.
    price = (price // min_price_increment) * min_price_increment
    logger.info(f'Цена в пунктах: {price}')
    logger.info(f'Цена в рублях: {price_in_rub}')
    order_params = {
        'instrument_id': context.history_instrument.instrument_info.uid,
        'quantity': ut.calculation_quantity(price_rub_one_point=price_rub_point,
                                            portfolio=portfolio_size,
                                            atr=context.history_instrument.atr),
        'price': decimal_to_quotation(price),
        'direction': OrderDirection.ORDER_DIRECTION_BUY if long else OrderDirection.ORDER_DIRECTION_SELL,
        'account_id': ACCOUNT_ID,
        'order_type': OrderType.ORDER_TYPE_LIMIT,
        'order_id': order_id
    }
    logger.info(f'Выставляем ордер по {context.history_instrument.instrument_info.name}'
                f' на {order_params["quantity"]} лотов по цене {decimal_to_quotation(Decimal(price))}')
    # logger.info(f"params: {'\n'.join(f'{k}: {v}' for k, v in order_params.items())}")
    result: PostOrderResponse = await connect.post_order(**order_params)
    order_response_id = result.order_id
    logger.info(f'Получен ответ по выставленному поручению'
                f' {context.history_instrument.instrument_info.name} {result.execution_report_status}')

    await asyncio.sleep(10)
    list_order_state = []
    order_state = None
    for _ in range(count):
        try:
            logger.info(f'Ждем подтверждения ордера {count} раз с интервалом {retry_interval} сек.')
            order_state: OrderState = await connect.client.orders.get_order_state(order_id=order_response_id,
                                                                                  account_id=ACCOUNT_ID)
            # Обработка успешно выполненного ордера
            if order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL:
                logger.info(f'Заявка выполнена {order_state}')
                list_order_state.append(order_state)
                return list_order_state
            # Обработка нового ордера, без выполненных лотов
            elif order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW:
                print(dict_last_price)
                if context.history_instrument.instrument_info.figi in dict_last_price:
                    if compare_price(new_price=dict_last_price[context.history_instrument.instrument_info.figi],
                                     order_state=order_state,
                                     atr=context.history_instrument.atr,
                                     context=context):
                        new_order = await replace_order(connect, context,
                                                        order_response_id, order_state,
                                                        price, min_price_increment)
                        order_response_id = new_order.order_id
                        list_order_state.append(order_state)
                        continue
                logger.info(f'Заявка ожидает выполнения {order_state}, повторяем попытку через {retry_interval} сек.')
                await asyncio.sleep(retry_interval)
                continue
            # Обработка частично выполненного ордера
            elif (order_state.execution_report_status ==
                  OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_PARTIALLYFILL):
                if context.history_instrument.instrument_info.figi in dict_last_price:
                    if compare_price(new_price=dict_last_price[context.history_instrument.instrument_info.figi],
                                     order_state=order_state,
                                     atr=context.history_instrument.atr,
                                     context=context):
                        new_order = await replace_order(connect, context,
                                                        order_response_id, order_state,
                                                        price, min_price_increment)
                        order_response_id = new_order.order_id
                        list_order_state.append(order_state)
                        continue
                logger.info(f'Заявка частично выполнена {order_state}, повторяем попытку через {retry_interval} сек.')
                logger.info(f'Выполнено лотов {order_state.lots_executed} / {order_state.lots_requested}')
                await asyncio.sleep(retry_interval)
                continue
            # Обработка отмененного ордера.
            elif order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_CANCELLED:
                logger.info(f'Заявка отменена {order_state.execution_report_status.name}')
                if order_state.lots_executed > 0:
                    logger.info(f'Выполнено лотов {order_state.lots_executed} / {order_state.lots_requested}')
                    list_order_state.append(order_state)
                    return list_order_state
                else:
                    logger.info(f'Заявка отменена {order_state.execution_report_status.name}')
                    logger.info(f'Выполнено 0 лотов')
                    raise Exception(f'Заявка не выполнена {order_state.execution_report_status.name}')
            # Обработка отклоненного ордера.
            elif order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_REJECTED:
                logger.info(f'Заявка отклонена {order_state.execution_report_status.name}')
                raise Exception(f'Заявка отклонена {order_state.execution_report_status.name}')

        # Обработка ошибок во время выставления ордера.
        except Exception as e:
            if order_state:
                if order_state.lots_executed > 0:
                    logger.info(f'Выполнено лотов {order_state.lots_executed} / {order_state.lots_requested}')
                    logger.error(f'При ожидании заявки произошла ошибка {e}')
                    list_order_state.append(order_state)
                    return list_order_state
                else:
                    raise Exception(f'Заявка не выполнена {e}')
    # Обработка ситуации когда бот не дождался выполнения заявки.
    else:
        logger.info(f'Заявка не выполнена за {count * retry_interval} сек.')
        try:
            time_cancel = await connect.client.orders.cancel_order(account_id=ACCOUNT_ID, order_id=order_response_id)
            logger.info(f'Заявка на {context.history_instrument.instrument_info.name} '
                        f'{order_state.lots_executed} / {order_state.lots_requested} '
                        f'лотов отменена в {time_cancel}')
        except Exception as e:
            logger.error(f'При отмене заявки произошла ошибка {e}')
        if order_state.lots_executed > 0:
            logger.info(f'Выполнено лотов {order_state.lots_executed} / {order_state.lots_requested}')
            list_order_state.append(order_state)
            return list_order_state
        else:
            raise Exception(f'Заявка не выполнена за {count * retry_interval} сек.')


async def order_for_close_position(context: 'StrategyContext', connect: ConnectTinkoff,
                                   price: Decimal, count: int = 100,
                                   retry_interval=10) -> Optional[list[OrderState]]:
    logger.info(f'Закрытие позиции {context.history_instrument.instrument_info.name} по цене {price}')
    order_id = ut.generate_order_id()
    min_price_increment = quotation_to_decimal(context.history_instrument.instrument_info.min_price_increment)
    price = (price // min_price_increment) * min_price_increment
    order_params = {
        'instrument_id': context.history_instrument.instrument_info.uid,
        'quantity': context.quantity,
        'price': price,
        'direction': context.close_direction,
        'account_id': ACCOUNT_ID,
        'order_type': OrderType.ORDER_TYPE_LIMIT,
        'order_id': order_id
    }
    result = await connect.post_order(**order_params)
    logger.info(f'Получен ответ по выставленному поручению'
                f' {context.history_instrument.instrument_info.name} {result.execution_report_status}')
    order_response_id = result.order_id
    list_order_state = []
    order_state = None
    await asyncio.sleep(retry_interval)
    for _ in range(count):
        try:
            order_state = await connect.client.orders.get_order_state(order_id=order_response_id,
                                                                      account_id=ACCOUNT_ID)
            if order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL:
                logger.info(f'Позиция {context.history_instrument.instrument_info.name} закрыта')
                list_order_state.append(order_state)
                return list_order_state

            elif order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_REJECTED:
                logger.info(f'Закрытие позиции: Заявка отклонена {order_state.execution_report_status.name}')
                raise Exception(f'Закрытие позиции: Заявка отклонена {order_state.execution_report_status.name}')

            elif order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_CANCELLED:
                logger.info(f'Закрытие позиции: Заявка отменена {order_state.execution_report_status.name}')
                if order_state.lots_executed > 0:
                    list_order_state.append(order_state)
                    logger.info(f'Закрытие позиции: Позиция {context.history_instrument.instrument_info.name} закрыта'
                                f'не полностью {order_state.lots_executed} / {order_state.lots_requested} лотов')
                    list_order_state.append(False)
                    return list_order_state
                else:
                    raise Exception(f'Закрытие позиции: Заявка отменена {order_state.execution_report_status.name}')

            elif order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW:
                if context.history_instrument.instrument_info.figi in dict_last_price:
                    if compare_price(new_price=dict_last_price[context.history_instrument.instrument_info.figi],
                                     order_state=order_state,
                                     atr=context.history_instrument.atr,
                                     context=context):
                        new_order = await replace_order(connect=connect, context=context,
                                                        order_response_id=order_response_id,
                                                        order_state=order_state, price=price,
                                                        min_price_increment=min_price_increment)
                        order_response_id = new_order.order_id
                        list_order_state.append(order_state)
                        await asyncio.sleep(retry_interval)
                        continue
                logger.info(f'Закрытие позиции: Заявка ожидает выполнения {order_state.execution_report_status.name}')
                await asyncio.sleep(retry_interval)
                continue

            elif (order_state.execution_report_status ==
                  OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_PARTIALLYFILL):
                if context.history_instrument.instrument_info.figi in dict_last_price:
                    if compare_price(new_price=dict_last_price[context.history_instrument.instrument_info.figi],
                                     order_state=order_state,
                                     atr=context.history_instrument.atr,
                                     context=context):
                        new_order = await replace_order(connect=connect, context=context,
                                                        order_response_id=order_response_id,
                                                        order_state=order_state, price=price,
                                                        min_price_increment=min_price_increment)
                        order_response_id = new_order.order_id
                        list_order_state.append(order_state)
                        await asyncio.sleep(retry_interval)
                        continue
                logger.info(f'Закрытие позиции: Заявка частично выполнена {order_state.execution_report_status.name}')
                await asyncio.sleep(retry_interval)
                continue

        except Exception as e:
            if order_state:
                if order_state.lots_executed > 0:
                    list_order_state.append(order_state)
                    list_order_state.append(False)
                    logger.error(f'Закрытие позиции: При выполнении заявки произошла ошибка {e}')
                    return list_order_state
                else:
                    raise Exception(f'Закрытие позиции: Заявка не выполнена {e}')

    else:
        logger.info(f'Закрытие позиции: Заявка не выполнена за {count * retry_interval} сек.')
        try:
            time_cancel = await connect.client.orders.cancel_order(account_id=ACCOUNT_ID, order_id=order_response_id)
            logger.info(f'Закрытие позиции: Заявка на {context.history_instrument.instrument_info.name} '
                        f'{order_state.lots_executed} / {order_state.lots_requested} '
                        f'лотов отменена в {time_cancel}')
            list_order_state.append(order_state)
            list_order_state.append(False)
            return list_order_state
        except Exception as e:
            raise Exception(f'При отмене заявки произошла ошибка {e}')


async def replace_order(connect: 'ConnectTinkoff', context, order_response_id, order_state, price, min_price_increment):
    logger.info(f'Цена изменилась, меняем цену ордера на величину {context.history_instrument.atr}')
    new_price = (price + (context.history_instrument.atr / Decimal(2)) if
                 order_state.direction == OrderDirection.ORDER_DIRECTION_BUY
                 else price - (context.history_instrument.atr / Decimal(2)))
    new_order_id = ut.generate_order_id()
    new_price = (new_price // min_price_increment) * min_price_increment
    order_params = {
        'account_id': ACCOUNT_ID,
        'order_id': order_response_id,
        'price': decimal_to_quotation(new_price),
        'quantity': order_state.lots_requested - order_state.lots_executed,
        'idempotency_key': new_order_id,
        'price_type': PriceType.PRICE_TYPE_POINT
    }
    new_order = await connect.client.orders.replace_order(**order_params)
    return new_order


async def get_rub_price(connect, context, price) -> tuple[Decimal, Decimal, Decimal]:
    margin_response: GetFuturesMarginResponse = await connect.client.instruments.get_futures_margin(
        instrument_id=context.history_instrument.instrument_info.uid
    )
    min_price_increment = margin_response.min_price_increment
    min_price_increment_amount = margin_response.min_price_increment_amount

    price_rub_point = ((Decimal(1) / quotation_to_decimal(min_price_increment)) *
                       quotation_to_decimal(min_price_increment_amount))
    price_rub_point = Decimal(price_rub_point)

    price_in_rub = ((Decimal(price) / quotation_to_decimal(min_price_increment))
                    * quotation_to_decimal(min_price_increment_amount))
    price_in_rub = Decimal(price_in_rub)

    return price_rub_point, price_in_rub, quotation_to_decimal(min_price_increment)


if __name__ == '__main__':
    pass
