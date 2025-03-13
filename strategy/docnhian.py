from __future__ import annotations

import abc
import datetime
from datetime import timedelta
from decimal import Decimal
from typing import Any

from tinkoff.invest import OrderState, OrderDirection, GetOperationsByCursorRequest, OperationType, \
    GetOperationsByCursorResponse, PortfolioPosition, OperationItem
from tinkoff.invest.utils import money_to_decimal, now, quotation_to_decimal

from bot.telegram_bot import logger
from config import ACCOUNT_ID
from data_create.historic_future import HistoricInstrument
from trad.connect_tinkoff import ConnectTinkoff
from trad.task_all_time import place_order_with_status_check, order_for_close_position


def update_strategy_context(my_context: 'StrategyContext',
                            result: list[OrderState],
                            long: bool):
    entry_price = Decimal(sum(money_to_decimal(x.average_position_price) for x in result) / len(result))
    min_increment_amount = quotation_to_decimal(
        my_context.history_instrument.instrument_info.min_price_increment_amount)
    min_increment = quotation_to_decimal(my_context.history_instrument.instrument_info.min_price_increment)
    entry_price = ((entry_price / min_increment_amount) * min_increment).quantize(Decimal('1.00'),
                                                                                  rounding='ROUND_HALF_EVEN')
    my_context.position_units += 1
    my_context.state = TradeOpenState()
    if long:
        my_context.long = True
        my_context.short = False
        my_context.stop_levels.append(entry_price - (Decimal(0.5) * my_context.history_instrument.atr))
    else:
        my_context.long = False
        my_context.short = True
        my_context.stop_levels.append(entry_price + (Decimal(0.5) * my_context.history_instrument.atr))
    my_context.quantity += int(sum(x.lots_executed for x in result))
    my_context.order_state.append(result)
    my_context.entry_prices.append(entry_price)
    if my_context.position_units == 1:
        logger.info(
            f"[{my_context.history_instrument.instrument_info.name} открыта позиция "
            f"{'long' if my_context.long else 'short'} точка входа {entry_price:.4f}"
        )
        my_context.start_position_date = min(x.order_date for x in result)
    elif 1 < my_context.position_units <= 4:
        logger.info(
            f"[{my_context.history_instrument.instrument_info.name} увеличение позиции {my_context.position_units} "
            f"{'long' if my_context.long else 'short'} точка входа {entry_price:.4f}"
        )


# Базовый класс для состояний стратегии
class StrategyState(abc.ABC):
    @abc.abstractmethod
    async def on_new_price(self, context: 'StrategyContext',
                           price: float,
                           connect: ConnectTinkoff):
        """
        Обработка нового ценового обновления и переход к следующему состоянию, если необходимо.
        """
        pass


# Состояние "Ожидание пробоя" – нет открытой сделки, ждём пробоя канала
class IdleState(StrategyState):
    async def on_new_price(self, context: 'StrategyContext',
                           price: Decimal,
                           connect: ConnectTinkoff):
        # Проверяем пробой канала на лонг.
        if price >= context.breakout_level_long + context.history_instrument.tick_size:
            logger.info(f"{context.history_instrument.instrument_info.name} сработал пробой канала {price:.2f} - long")
            entry: Decimal = context.breakout_level_long + context.history_instrument.tick_size
            try:
                result: list[OrderState] = await place_order_with_status_check(connect=connect, context=context,
                                                                               price=entry, long=True)
                update_strategy_context(my_context=context, result=result, long=True)
                return True
            except Exception as e:
                logger.error(f'При выставлении ордера произошла ошибка{e}')
            return False

        # Проверяем пробой канала на шорт.
        elif price < context.breakout_level_short - context.history_instrument.tick_size:
            logger.info(f"{context.history_instrument.instrument_info.name} сработал пробой канала {price:.2f} - short")
            entry = context.breakout_level_short - context.history_instrument.tick_size
            try:  # Выставление ордера и изменение статуса позиции.
                result: list[OrderState] = await place_order_with_status_check(connect=connect, context=context,
                                                                               price=entry, long=False)
                update_strategy_context(my_context=context, result=result, long=False)
                return True
            except Exception as e:
                logger.error(f'При выставлении ордера произошла ошибка{e}')
                return False
        else:
            return False


def close_context(context: 'StrategyContext') -> None:
    context.start_position_date = None
    context.long = None
    context.short = None
    context.max_units = 4
    context.position_units = 0
    context.entry_prices = []
    context.stop_levels = []
    context.quantity = 0
    context.portfolio_position = None
    context.order_state = []
    context.operation_list = []
    context.state = IdleState()
    context.no_close = None


# Состояние "Открытая сделка" – позиция открыта, можно добавлять юниты или закрывать сделку.
class TradeOpenState(StrategyState):

    async def on_new_price(self, context: 'StrategyContext', price: float, connect: ConnectTinkoff):
        last_entry: Decimal = context.entry_prices[-1]

        # Проверяем условие для увеличения позиции на лонг.
        if (context.position_units < context.max_units
                and price >= last_entry + (Decimal(0.5) * context.history_instrument.atr)
                and context.long):
            logger.info(f"{context.history_instrument.instrument_info.name} "
                        f"переход на этап {context.position_units + 1} - {price:.2f} - long")
            try:
                entry: Decimal = last_entry + (Decimal(0.5) * context.history_instrument.atr)
                result: list[OrderState] = await place_order_with_status_check(connect=connect, context=context,
                                                                               price=entry, long=True)
                update_strategy_context(my_context=context, result=result, long=True)
                return True
            except Exception as e:
                logger.error(f'При выставлении ордера произошла ошибка{e}')
                return False

        # Проверяем условие для увеличения позиции на шорт.
        elif (context.position_units < context.max_units
              and price <= last_entry - (Decimal(0.5) * context.history_instrument.atr)
              and context.short):
            logger.info(f"{context.history_instrument.instrument_info.name} "
                        f"переход на этап {context.position_units + 1} - {price:.2f} - short")
            try:
                entry: Decimal = last_entry - (Decimal(0.5) * context.history_instrument.atr)
                result: list[OrderState] = await place_order_with_status_check(connect=connect, context=context,
                                                                               price=entry, long=False)
                update_strategy_context(my_context=context, result=result, long=False)
                return True
            except Exception as e:
                logger.error(f'При выставлении ордера произошла ошибка{e}')
                return False

        # Проверяем условие для закрытия позиции — лонг.
        elif price < context.stop_levels[-1] and context.long:
            logger.info(f"{context.history_instrument.instrument_info.name}-"
                        f"закрытие позиции {context.position_units} - {price:.2f} - long")
            close_price: Decimal = context.stop_levels[-1]
            try:
                result: list[OrderState] = await order_for_close_position(context, connect, close_price)
                if not result[-1]:
                    logger.info(f'Позиция по {context.history_instrument.instrument_info.name} '
                                f'закрыта не полностью')
                    try:
                        context.quantity = context.quantity - int(sum(x.lots_executed for x in result[:-1]))
                    except IndexError:
                        context.quantity = 0
                    context.no_close = True
                    return True
                else:
                    logger.info(f'Позиция по {context.history_instrument.instrument_info.name} '
                                f'закрыта')
                    close_context(context)
                    return True
            except Exception as e:
                logger.error(f'При закрытии позиции по {context.history_instrument.instrument_info.name} '
                             f'произошла ошибка {e}')
                return False

        # Проверяем условие для закрытия позиции — шорт.
        elif price > context.stop_levels[-1] and context.short:
            logger.info(f"{context.history_instrument.instrument_info.name}-"
                        f"закрытие позиции {context.position_units} - {price:.2f} - short")
            close_price: Decimal = context.stop_levels[-1]
            try:
                result: list[OrderState] = await order_for_close_position(context, connect, close_price)
                if not result[-1]:
                    logger.info(f'Позиция по {context.history_instrument.instrument_info.name} '
                                f'закрыта не полностью')
                    try:
                        context.quantity = context.quantity - int(sum(x.lots_executed for x in result[:-1]))
                    except IndexError:
                        context.quantity = 0
                    context.no_close = True
                    return True
                else:
                    close_context(context)
                    return True
            except Exception as e:
                logger.error(f'При закрытии позиции по {context.history_instrument.instrument_info.name} '
                             f'произошла ошибка {e}')
                return False


# Контекст, хранящий состояние стратегии для конкретного инструмента
class StrategyContext:
    def __init__(self, history_instrument: HistoricInstrument):
        """
        :param history_instrument: Данные по инструменту, который будет торговаться по этой стратегии
        """
        self.history_instrument: HistoricInstrument = None
        self.breakout_level_long: Decimal = None
        self.breakout_level_short: Decimal = None
        self.exit_long_donchian: Decimal = None
        self.exit_short_donchian: Decimal = None

        self.start_position_date: datetime.datetime = None
        self.long: bool = None
        self.short: bool = None
        self.max_units: int = 4
        self.position_units: int = 0
        self.entry_prices: list[Decimal] = []
        self.stop_levels: list[Decimal] = []
        self.quantity: Decimal = 0
        self.portfolio_position: PortfolioPosition = None
        self.order_state: list[list[OrderState]] = []
        self.operation_list: list[OperationItem] = []
        self.state: StrategyState = IdleState()
        self.no_close = None

        self.update_data(history_instrument)

    def update_data(self, history_instrument: HistoricInstrument):
        self.history_instrument: HistoricInstrument = history_instrument
        self.breakout_level_long: Decimal = self.history_instrument.max_donchian
        self.breakout_level_short: Decimal = self.history_instrument.min_donchian
        self.exit_long_donchian: Decimal = self.history_instrument.min_short_donchian
        self.exit_short_donchian: Decimal = self.history_instrument.max_short_donchian
        # Замена стоп лосса торговой стратегии при позиции в 4 юнита.
        if self.max_units >= 4 and self.long and self.stop_levels[-1] < self.exit_long_donchian:
            self.stop_levels.append(self.exit_long_donchian)
        elif self.max_units >= 4 and self.short and self.stop_levels[-1] > self.exit_short_donchian:
            self.stop_levels.append(self.exit_short_donchian)

    @property
    def direction(self) -> OrderDirection:
        if self.long:
            return OrderDirection.ORDER_DIRECTION_BUY
        elif self.short:
            return OrderDirection.ORDER_DIRECTION_SELL
        else:
            return None

    @property
    def close_direction(self) -> OrderDirection:
        if self.long:
            return OrderDirection.ORDER_DIRECTION_SELL
        elif self.short:
            return OrderDirection.ORDER_DIRECTION_BUY
        else:
            return None

    async def on_new_price(self, price: Decimal, connect: ConnectTinkoff):
        result = await self.state.on_new_price(self, price, connect)
        return result

    def current_position_info(self) -> dict[str, Any]:
        return {
            "name": self.history_instrument.instrument_info.name,
            "units": self.position_units,
            "entry_prices": self.entry_prices,
            "quantity": self.quantity,
            "stop_levels": self.stop_levels,
            'direction': self.direction.name if self.direction else None,
            "state": self.state.__class__.__name__,
            "atr": self.history_instrument.atr,
            "breakout_level_long": self.breakout_level_long,
            "breakout_level_short": self.breakout_level_short,
            "start_position_date": (self.start_position_date.strftime("%Y-%m-%d %H:%M:%S")
                                    if self.start_position_date else None),
            "no_close": self.no_close
        }

    async def update_position_info(self, connect: ConnectTinkoff, portfolio: PortfolioPosition = None):
        """
        Обновляет информацию о текущей позиции.
        """
        request = GetOperationsByCursorRequest(
            account_id=ACCOUNT_ID,
            from_=self.start_position_date if self.start_position_date else now() - timedelta(
                days=100),
            to=now(),
            instrument_id=self.history_instrument.instrument_info.uid,
            operation_types=[OperationType.OPERATION_TYPE_BUY, OperationType.OPERATION_TYPE_SELL],
        )
        operations_response: GetOperationsByCursorResponse = await connect.client.operations.get_operations_by_cursor(
            request=request
        )

        operations_response.items = [item for item in operations_response.items if item.quantity_done > 0]

        def calculate_stop_level(history_instrument, item, long) -> Decimal:
            if long:
                return money_to_decimal(item.price) - (Decimal(0.5) * Decimal(history_instrument.atr))
            else:
                return money_to_decimal(item.price) + (Decimal(0.5) * Decimal(history_instrument.atr))

        if portfolio:
            self.quantity = int(quotation_to_decimal(portfolio.quantity))
            self.portfolio_position = portfolio
        else:
            self.quantity = 0

        if self.quantity > 0:
            self.position_units = len([item for item in
                                       operations_response.items if
                                       item.type == OperationType.OPERATION_TYPE_BUY and
                                       item.quantity_done == item.quantity])
            self.start_position_date = sorted(operations_response.items, key=lambda item_trade: item_trade.date)[0].date
            self.operation_list = operations_response.items
            self.long = True
            self.short = False
            self.state = TradeOpenState()
            self.entry_prices = [money_to_decimal(item.price) for item in operations_response.items
                                 if item.type == OperationType.OPERATION_TYPE_BUY and
                                 item.quantity_done > 0]
            self.stop_levels = [calculate_stop_level(self.history_instrument, item, True) for item
                                in operations_response.items
                                if item.type == OperationType.OPERATION_TYPE_BUY and
                                item.quantity_done > 0]
        elif self.quantity < 0:
            self.position_units = len([item for item in
                                       operations_response.items
                                       if item.type == OperationType.OPERATION_TYPE_SELL and
                                       item.quantity_done > 0])
            self.start_position_date = sorted(operations_response.items, key=lambda item_trade: item_trade.date)[0].date
            self.operation_list = operations_response.items
            self.long = False
            self.short = True
            self.state = TradeOpenState()
            self.entry_prices = [money_to_decimal(item.price) for item in operations_response.items
                                 if item.type == OperationType.OPERATION_TYPE_SELL and
                                 item.quantity_done > 0]
            self.stop_levels = [calculate_stop_level(self.history_instrument, item, False) for item
                                in operations_response.items
                                if item.type == OperationType.OPERATION_TYPE_SELL and
                                item.quantity_done > 0]

        else:
            self.start_position_date: datetime.datetime = None
            self.long: bool = None
            self.short: bool = None
            self.max_units: int = 4
            self.position_units: int = 0
            self.entry_prices: list[Decimal] = []
            self.stop_levels: list[Decimal] = []
            self.quantity: int = 0
            self.portfolio_position: PortfolioPosition = None
            self.order_state: list[OrderState] = []
            self.operation_list: list[OperationItem] = []
            self.state: StrategyState = IdleState()
            self.no_close = None


if __name__ == '__main__':
    pass
