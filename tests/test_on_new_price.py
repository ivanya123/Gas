import asyncio
import pickle
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import tinkoff.invest as ti

from strategy.docnhian import StrategyContext, IdleState, TradeOpenState
from trad.connect_tinkoff import ConnectTinkoff
import tests.scripts as s
import utils as ut


# TODO: text on_new_price long and short
# TODO text on_new_price Exception
@pytest.mark.asyncio
async def test_on_new_price_long(monkeypatch):
    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
        fake_context = [context for context in dict_strategy_state.values() if isinstance(context.state, IdleState)][0]

        price = fake_context.breakout_level_long + fake_context.tick_size + 1
    fake_order_trades = s.fabrics_order_trades(
        ti.OrderTrades(
            order_id='111',
            trades=[ti.OrderTrade(
                quantity=ut.calculation_quantity(price, fake_context.portfolio_size, fake_context.atr))
            ]
        )
    )

    monkeypatch.setattr('strategy.docnhian.place_order_with_status_check',
                        AsyncMock(return_value=fake_order_trades))

    fake_connect = ConnectTinkoff('TOKEN')

    result = await fake_context.on_new_price(price=price, connect=fake_connect)

    assert result == True
    assert isinstance(fake_context.state, TradeOpenState) == True
    assert len(fake_context.entry_prices) == 1
    assert fake_context.long == True
    assert fake_context.short == None
    assert fake_context.quantity == ut.calculation_quantity(price, fake_context.portfolio_size, fake_context.atr)


@pytest.mark.asyncio
async def test_on_new_price_no_change(monkeypatch):
    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
        fake_context = \
            [context for context in dict_strategy_state.values() if isinstance(context.state, IdleState)][0]

        price = fake_context.breakout_level_long + fake_context.tick_size + 1
    fake_order_trades = s.fabrics_order_trades(
        ti.OrderTrades(
            order_id='111',
            trades=[ti.OrderTrade(
                quantity=ut.calculation_quantity(price, fake_context.portfolio_size, fake_context.atr))
            ]
        )
    )

    monkeypatch.setattr('strategy.docnhian.place_order_with_status_check',
                        AsyncMock(return_value=fake_order_trades))

    fake_connect = ConnectTinkoff('TOKEN')

    result = await fake_context.on_new_price(price=price, connect=fake_connect)

    assert result == True
    assert isinstance(fake_context.state, TradeOpenState) == True
    assert len(fake_context.entry_prices) == 1
    assert fake_context.long == True
    assert fake_context.short == None
    assert fake_context.quantity == ut.calculation_quantity(price, fake_context.portfolio_size, fake_context.atr)


if __name__ == '__main__':
    pytest.main()
