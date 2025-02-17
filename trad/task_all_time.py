import asyncio

import pickle
from typing import Optional

from aiogram import Bot
from tinkoff.invest import MarketDataResponse, PortfolioStreamResponse, PositionsStreamResponse, TradesStreamResponse, \
    OrderTrades, OrderState, OrderDirection, OrderType, OrderExecutionReportStatus
from tinkoff.invest.utils import quotation_to_decimal, money_to_decimal

from bot.telegram_bot import logger
from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from data_create.historic_future import HistoricInstrument
from config import CHAT_ID, ACCOUNT_ID, TOKEN_D
import utils as ut

event_stop_stream_to_chat = asyncio.Event()
event_update = asyncio.Event()
dict_status_instrument = {}


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
                    result = ut.update_strategy_by_price(last_price, msg)
                    if result:
                        await bot.send_message(chat_id=CHAT_ID, text=result)
                except Exception as e:
                    logger.error(e)
            if msg.trading_status:
                msg_str = ut.market_data_response_to_string(msg) + '\n'
                dict_status_instrument[msg.trading_status.instrument_uid] = msg.trading_status.trading_status
                await bot.send_message(chat_id=CHAT_ID, text=msg_str)
            if msg.subscribe_info_response or msg.subscribe_last_price_response:
                msg_str = ut.market_data_response_to_string(msg) + '\n'
                await bot.send_message(chat_id=CHAT_ID, text=msg_str)


async def processing_stream_portfolio(connect: ConnectTinkoff, bot: Bot):
    while True:
        response: PortfolioStreamResponse | PositionsStreamResponse = await connect.queue_portfolio.get()
        if isinstance(response, PortfolioStreamResponse):
            text, portfolio_amount = ut.psr_to_string(response)
            await bot.send_message(chat_id=CHAT_ID, text=text)
            ut.update_all_portfolio_size(portfolio_amount)
        if isinstance(response, PositionsStreamResponse):
            text = ut.posr_to_string(response)
            if not response.ping:
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


async def waiting_order_accept(context: StrategyContext):
    while dict_queue.get(context.instrument_figi) is None:
        logger.debug(f'Ожидаем подтверждения ордера {ut.figi_to_name(context.instrument_figi)}')
        await asyncio.sleep(0.5)
    order_trades: OrderTrades = await dict_queue[context.instrument_figi].get()
    return order_trades


async def place_order_with_status_check(connect: ConnectTinkoff,
                                        context: StrategyContext,
                                        price: float,
                                        long: bool,
                                        timeout: int = 30,
                                        retry_interval: int = 10,
                                        ) -> Optional[OrderTrades | OrderState]:
    """
       Выставляет ордер и ждет его подтверждения. При таймауте запрашивает статус ордера.
       Если ордер в состоянии ожидания (pending), повторно ждёт подтверждения.

       :param connect: объект подключения (например, ConnectTinkoff)
       :param context: объект StrategyContext для текущего инструмента
       :param price: цена, по которой выставляется ордер
       :param long: направление ордера (True - лонг, False - шорт)
       :param timeout: время ожидания подтверждения ордера (в секундах)
       :param retry_interval: интервал между повторными попытками (в секундах)
       :return: статус ордера или ошибка, если ордер отменён/не принят
       """
    order_id = ut.generate_order_id()
    order_params = {
        'instrument_id': context.instrument_uid,
        'quantity': ut.calculation_quantity(price, context.portfolio_size, context.atr),
        'price': price,
        'direction': OrderDirection.ORDER_DIRECTION_BUY if long else OrderDirection.ORDER_DIRECTION_SELL,
        'account_id': ACCOUNT_ID,
        'order_type': OrderType.ORDER_TYPE_LIMIT,
        'order_id': order_id
    }
    logger.info(f'Выставляем ордер по {ut.figi_to_name(context.instrument_figi)}'
                f' на {order_params["quantity"]} лотов по цене {price}')
    result = await connect.post_order(**order_params)
    order_id = order_params['order_id']
    logger.info(f'Получен ответ по выставленному поручению'
                f' {ut.figi_to_name(context.instrument_figi)} {result.execution_report_status}')

    async def wait_for_order_accept():
        return await waiting_order_accept(context)

    count = 0
    while True:
        try:
            logger.info(f'Ждем подтверждения ордера {timeout} сек.')
            order_status: OrderTrades = await asyncio.wait_for(wait_for_order_accept(), timeout=timeout)
            logger.info(f"Заявка выполнена {order_status}")
            return order_status
        except asyncio.TimeoutError:
            logger.info(f'Таймаут истек, запрашиваем статус ордера')
            order_state: OrderState = await connect.client.orders.get_order_state(order_id)
            if order_state.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL:
                logger.info(f'Заявка выполнена {order_state}')
                return order_state
            elif (order_state.execution_report_status
                  == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_PARTIALLYFILL) or (
                    order_state.execution_report_status
                    == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_NEW
            ):
                logger.info(f'Заявка частично выполнена {order_state}, повторяем попытку через {retry_interval} сек.')
                count += 1
                if count == 10:
                    logger.info(f'Заявка не выполнена {order_state}, отменяем')
                    await connect.client.orders.cancel_order(order_id)
                    return
                else:
                    await asyncio.sleep(retry_interval)
                continue
            else:
                logger.info(f'Заявка не выполнена {order_state}')
                raise Exception(f'Заявка не выполнена {order_state}')


if __name__ == '__main__':
    async def main():
        connect = ConnectTinkoff(TOKEN_D)
        await connect.connect()
        await conclusion_in_day(connect, 1)


    asyncio.run(main())
