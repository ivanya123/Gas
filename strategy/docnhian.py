import abc
import pickle

from tinkoff.invest import OrderDirection, OrderType

from config import ACCOUNT_ID
from data_create.historic_future import HistoricInstrument
import utils as ut
from trad.connect_tinkoff import ConnectTinkoff


# Базовый класс для состояний стратегии
class StrategyState(abc.ABC):
    @abc.abstractmethod
    def on_new_price(self, context: 'StrategyContext', price: float, connect: ConnectTinkoff):
        """
        Обработка нового ценового обновления и переход к следующему состоянию, если необходимо.
        """
        pass


# Состояние "Ожидание пробоя" – нет открытой сделки, ждём пробоя канала
class IdleState(StrategyState):
    async def on_new_price(self, context: 'StrategyContext', price: float, connect: ConnectTinkoff):
        if price >= context.breakout_level_long + context.tick_size:
            entry = price
            context.entry_prices.append(entry)
            kwargs = {
                'instrument_id': context.instrument_uid,
                'quantity': ut.calculation_quantity(price, context.portfolio_size, context.atr),
                'price': price,
                'direction': OrderDirection.ORDER_DIRECTION_BUY,
                'account_id': ACCOUNT_ID,
                'order_type': OrderType.ORDER_TYPE_LIMIT,
                'order_id': ut.generate_order_id()
            }
            result = await connect.post_order(**kwargs)
            context.position_units = 1
            context.stop_levels.append(entry - 0.5 * context.atr)
            context.state = TradeOpenState()
            context.long = True
            print(f"[{context.instrument_figi}] Trade opened at long {entry:.4f}")
            return True
        elif price < context.breakout_level_short - context.tick_size:
            entry = price
            context.entry_prices.append(entry)
            context.position_units = 1
            context.stop_levels.append(entry + 0.5 * context.atr)
            context.state = TradeOpenState()
            context.short = True
            print(f"[{context.instrument_figi}] Trade opened short at {entry:.4f}")
            return True
        else:
            pass


# Состояние "Открытая сделка" – позиция открыта, можно добавлять юниты или закрывать сделку
class TradeOpenState(StrategyState):
    def on_new_price(self, context: 'StrategyContext', price: float):
        last_entry = context.entry_prices[-1]
        if context.position_units < context.max_units and price >= last_entry + 0.5 * context.atr and context.long:
            new_entry = price
            context.entry_prices.append(new_entry)
            context.position_units += 1
            context.stop_levels.append(new_entry - 0.5 * context.atr)
            print(f"[{context.instrument_figi}] Added unit: now {context.position_units} units at {new_entry:.4f}")
            return True
        elif context.position_units < context.max_units and price <= last_entry - 0.5 * context.atr and context.short:
            new_entry = price
            context.entry_prices.append(new_entry)
            context.position_units += 1
            context.stop_levels.append(new_entry + 0.5 * context.atr)
            print(f"[{context.instrument_figi}] Added unit: now {context.position_units} units at {new_entry:.4f}")
            return True
        elif context.position_units == context.max_units and price >= last_entry - 0.5 * context.atr and context.long:
            new_entry = price
            context.entry_prices.append(new_entry)
            context.position_units += 1
            context.stop_levels.append(context.exit_long_donchian)
            print(f"[{context.instrument_figi}] Added unit: now {context.position_units} units at {new_entry:.4f}")
            return True
        elif context.position_units == context.max_units and price <= last_entry + 0.5 * context.atr and context.short:
            new_entry = price
            context.entry_prices.append(new_entry)
            context.position_units += 1
            context.stop_levels.append(context.exit_short_donchian)
            return True

        if price < context.stop_levels[-1] and context.long:
            context.state = ExitState()
            context.exit_price = price
            print(f"[{context.instrument_figi}] Stop triggered at {price:.4f}. Exiting trade.")
            return True
        if price > context.stop_levels[-1] and context.short:
            context.state = ExitState()
            context.exit_price = price
            print(f"[{context.instrument_figi}] Stop triggered at {price:.4f}. Exiting trade.")
            return True


class ExitState(StrategyState):
    def on_new_price(self, context: 'StrategyContext', price: float):
        print(f"[{context.instrument_figi}] Trade already closed at {context.exit_price:.4f}")


# Контекст, хранящий состояние стратегии для конкретного инструмента
class StrategyContext:
    def __init__(self, history_instrument: HistoricInstrument, portfolio_size: float, n: int):
        """
        :param history_instrument: Данные по инструрменту, который будет торговаться по этой стратегии
        :param portfolio_size: Размер портфеля (например, в долларах)
        :param n: Длина канала Дончяна (например, 20)
        """
        self.instrument_figi = history_instrument.instrument_info.figi
        self.name = history_instrument.instrument_info.name
        self.instrument_uid = history_instrument.instrument_info.uid
        self.ticker = history_instrument.instrument_info.ticker
        self.name = history_instrument.instrument_info.name
        self.portfolio_size = portfolio_size
        self.tick_size = float(history_instrument.tick_size)
        self.atr = history_instrument.atr
        self.n = n
        history_instrument.create_donchian_canal(n, int(n / 2))
        self.breakout_level_long = history_instrument.max_donchian
        self.breakout_level_short = history_instrument.min_donchian
        self.exit_long_donchian = history_instrument.min_short_donchian
        self.exit_short_donchian = history_instrument.max_short_donchian
        self.long = None
        self.short = None

        self.max_units = 4
        self.position_units = 0
        self.entry_prices = []
        self.stop_levels = []
        self.exit_price = None
        self.state: StrategyState = IdleState()

    def on_new_price(self, price: float):
        """
        При получении нового ценового обновления делегируем обработку текущему состоянию.
        """
        result = self.state.on_new_price(self, price)
        return result

    def current_position_info(self):
        """
        Возвращает информацию о текущей позиции.
        """
        return {
            "name": self.name,
            "instrument": self.instrument_figi,
            "units": self.position_units,
            "entry_prices": self.entry_prices,
            "stop_levels": self.stop_levels,
            "exit_price": self.exit_price,
            'long': self.long,
            'short': self.short,
            "state": self.state.__class__.__name__,
            "atr": self.atr,
            "breakout_level_long": self.breakout_level_long,
            "breakout_level_short": self.breakout_level_short,
        }

    def update_atr(self, history_instrument: HistoricInstrument):
        """
        Обновляет значение ATR для текущего инструмента.
        """
        history_instrument.create_donchian_canal(self.n, int(self.n / 2))
        self.atr = history_instrument.atr
        self.breakout_level_long = history_instrument.max_donchian
        self.breakout_level_short = history_instrument.min_donchian
        self.exit_long_donchian = history_instrument.min_short_donchian
        self.exit_short_donchian = history_instrument.max_short_donchian


# Пример использования:
if __name__ == '__main__':
    context = StrategyContext(
        history_instrument=HistoricInstrument.from_pkl(
            path=r'C:\Users\aples\PycharmProjects\Gas\IMOEXF Индекс МосБиржи\FUTIMOEXF000'),
        portfolio_size=100000,
        n=20
    )

    dict_strategy_context = {
        f'{context.instrument_figi}': context
    }

    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'wb') as f:
        pickle.dump(dict_strategy_context, f, protocol=pickle.HIGHEST_PROTOCOL)
