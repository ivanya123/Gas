import asyncio
import pickle
from unittest.mock import AsyncMock

import pytest
import tinkoff.invest as ti

from strategy.docnhian import StrategyContext
from trad.connect_tinkoff import ConnectTinkoff
from trad.task_all_time import place_order_with_status_check
import tests.scripts as s


@pytest.mark.asyncio
async def test_place_order_with_status_check(monkeypatch):
    fake_connect = ConnectTinkoff('TOKEN')

    fake_post_order_response = s.fabrics_post_order_response(
        ti.PostOrderResponse(order_id='111')
    )
    fake_connect.post_order = AsyncMock(return_value=fake_post_order_response)
    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
        fake_context = [context for context in dict_strategy_state.values()][0]

    fake_order_trades = s.fabrics_order_trades(
        ti.OrderTrades(
            order_id='111',
        )
    )
    monkeypatch.setattr('trad.task_all_time.waiting_order_accept', AsyncMock(return_value=fake_order_trades))

    result = await place_order_with_status_check(connect=fake_connect,
                                                 context=fake_context,
                                                 price=fake_context.breakout_level_long + 10,
                                                 long=True)
    assert result == fake_order_trades
    fake_connect.post_order.assert_called_once()


@pytest.mark.asyncio
async def test_waiting_order_accept(monkeypatch):
    fake_connect = ConnectTinkoff('TOKEN')
    fake_connect.client = s.FakeAsyncServices()
    fake_post_order_response = s.fabrics_post_order_response(
        ti.PostOrderResponse(order_id='111')
    )
    fake_connect.post_order = AsyncMock(return_value=fake_post_order_response)
    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
        fake_context = [context for context in dict_strategy_state.values()][0]

    fake_order_state = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_CANCELLED
        )
    )

    async def fake_waiting_order_accept(context: StrategyContext):
        context.n = context.n
        await asyncio.sleep(20)

    fake_connect.client.orders.get_order_state = AsyncMock(return_value=fake_order_state)
    monkeypatch.setattr('trad.task_all_time.waiting_order_accept', fake_waiting_order_accept)

    with pytest.raises(Exception) as e:
        await place_order_with_status_check(connect=fake_connect,
                                            context=fake_context,
                                            price=fake_context.breakout_level_long + 10,
                                            long=True,
                                            timeout=10)

    assert 'Заявка не выполнена' in str(e.value)
    fake_connect.post_order.assert_called_once()
    fake_connect.client.orders.get_order_state.assert_called_once()


@pytest.mark.asyncio
async def test_waiting_order_accept_timeout(monkeypatch):
    fake_connect = ConnectTinkoff('TOKEN')
    fake_connect.client = s.FakeAsyncServices()
    fake_post_order_response = s.fabrics_post_order_response(
        ti.PostOrderResponse(order_id='111')
    )
    fake_connect.post_order = AsyncMock(return_value=fake_post_order_response)
    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
        fake_context = [context for context in dict_strategy_state.values()][0]

    fake_order_state = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_PARTIALLYFILL
        )
    )

    async def fake_waiting_order_accept(context: StrategyContext):
        context.n = context.n
        await asyncio.sleep(3)

    fake_connect.client.orders.get_order_state = AsyncMock(return_value=fake_order_state)
    fake_connect.client.orders.cancel_order = AsyncMock()
    monkeypatch.setattr('trad.task_all_time.waiting_order_accept', fake_waiting_order_accept)

    result = await place_order_with_status_check(connect=fake_connect,
                                                 context=fake_context,
                                                 price=fake_context.breakout_level_long + 10,
                                                 long=True,
                                                 timeout=1,
                                                 retry_interval=1)

    assert result == fake_order_state
    fake_connect.post_order.assert_called_once()
    fake_connect.client.orders.get_order_state.assert_called()


@pytest.mark.asyncio
async def test_few_waiting_order_trades(monkeypatch):
    fake_connect = ConnectTinkoff('TOKEN')
    fake_connect.client = s.FakeAsyncServices()
    fake_post_order_response = s.fabrics_post_order_response(
        ti.PostOrderResponse(order_id='111')
    )
    fake_connect.post_order = AsyncMock(return_value=fake_post_order_response)
    with open(r'C:\Users\aples\PycharmProjects\Gas\dict_strategy_state.pkl', 'rb') as f:
        dict_strategy_state: dict[str, StrategyContext] = pickle.load(f)
        fake_context = [context for context in dict_strategy_state.values()][0]

    fake_order_trades = s.fabrics_order_trades(
        ti.OrderTrades(
            order_id='111',
        )
    )
    fake_order_state = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_PARTIALLYFILL
        )
    )

    fake_waiting_order_accept = AsyncMock(side_effect=[
        asyncio.TimeoutError(),
        asyncio.TimeoutError(),
        fake_order_trades
    ])

    fake_connect.client.orders.get_order_state = AsyncMock(return_value=fake_order_state)
    fake_connect.client.orders.cancel_order = AsyncMock()
    monkeypatch.setattr('trad.task_all_time.waiting_order_accept', fake_waiting_order_accept)

    result = await place_order_with_status_check(connect=fake_connect,
                                                 context=fake_context,
                                                 price=fake_context.breakout_level_long + 10,
                                                 long=True,
                                                 timeout=1,
                                                 retry_interval=1)

    assert result == fake_order_trades
    assert fake_waiting_order_accept.call_count == 3
    fake_connect.post_order.assert_called_once()
    fake_connect.client.orders.get_order_state.assert_called()


if __name__ == '__main__':
    pytest.main()
