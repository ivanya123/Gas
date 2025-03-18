import shelve
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import tinkoff.invest as ti
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation

import tests.scripts as s
from strategy.docnhian import StrategyContext, TradeOpenState, update_strategy_context
from trad.connect_tinkoff import ConnectTinkoff


# TODO: text on_new_price long and short
# TODO text on_new_price Exception
@pytest.mark.asyncio
async def test_on_new_price_close_one_units_long(monkeypatch):
    with shelve.open(r'data_test\database_test') as db:
        for key in db.keys():
            fake_context: StrategyContext = db[key]
            break

    fake_context.position_units = 1
    fake_context.entry_prices = [Decimal(100)]
    fake_context.stop_levels = [Decimal(95)]

    price_in_point: Decimal = fake_context.breakout_level_long + fake_context.history_instrument.tick_size
    price_in_rub = (price_in_point / quotation_to_decimal(
        fake_context.history_instrument.instrument_info.min_price_increment)) * quotation_to_decimal(
        fake_context.history_instrument.instrument_info.min_price_increment_amount)
    quotation_price = decimal_to_quotation(price_in_rub)

    fake_order_state = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            average_position_price=ti.MoneyValue(
                currency='RUB',
                units=quotation_price.units,
                nano=quotation_price.nano,
            ),
            lots_executed=4,
            order_date='2022-01-01T00:00:00',
        )
    )
    update_strategy_context(fake_context, [fake_order_state], long=True)

    fake_order_state_close = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            average_position_price=ti.MoneyValue(
                currency='RUB',
                units=quotation_price.units,
                nano=quotation_price.nano,
            ),
            lots_executed=2,
            order_date='2022-01-01T00:00:00',
        )
    )

    monkeypatch.setattr('strategy.docnhian.order_for_close_position',
                        AsyncMock(return_value=[fake_order_state_close]))

    fake_connect = ConnectTinkoff('TOKEN')

    price: Decimal = fake_context.stop_levels[-1] - Decimal(0.5)

    result = await fake_context.on_new_price(price=price, connect=fake_connect)

    assert fake_context.quantity == 2
    assert result == True
    assert isinstance(fake_context.state, TradeOpenState) == True
    assert len(fake_context.entry_prices) == 1
    assert fake_context.long == True
    assert fake_context.short == False
    assert fake_context.quantity == 2


@pytest.mark.asyncio
async def test_on_new_price_close_one_units_short(monkeypatch):
    with shelve.open(r'data_test\database_test') as db:
        for key in db.keys():
            fake_context: StrategyContext = db[key]
            break

    fake_context.position_units = 1
    fake_context.entry_prices = [Decimal(100)]
    fake_context.stop_levels = [Decimal(105)]

    price_in_point: Decimal = fake_context.breakout_level_short - fake_context.history_instrument.tick_size
    price_in_rub = (price_in_point / quotation_to_decimal(
        fake_context.history_instrument.instrument_info.min_price_increment)) * quotation_to_decimal(
        fake_context.history_instrument.instrument_info.min_price_increment_amount)
    quotation_price = decimal_to_quotation(price_in_rub)

    fake_order_state = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            average_position_price=ti.MoneyValue(
                currency='RUB',
                units=quotation_price.units,
                nano=quotation_price.nano,
            ),
            lots_executed=4,
            order_date='2022-01-01T00:00:00',
        )
    )
    update_strategy_context(fake_context, [fake_order_state], long=False)

    fake_order_state_close = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            average_position_price=ti.MoneyValue(
                currency='RUB',
                units=quotation_price.units,
                nano=quotation_price.nano,
            ),
            lots_executed=2,
            order_date='2022-01-01T00:00:00',
        )
    )

    monkeypatch.setattr('strategy.docnhian.order_for_close_position',
                        AsyncMock(return_value=[fake_order_state_close]))

    fake_connect = ConnectTinkoff('TOKEN')

    price: Decimal = fake_context.stop_levels[-1] + Decimal(0.5)

    result = await fake_context.on_new_price(price=price, connect=fake_connect)

    assert fake_context.quantity == 2
    assert result == True
    assert isinstance(fake_context.state, TradeOpenState) == True
    assert len(fake_context.entry_prices) == 1
    assert fake_context.short == True
    assert fake_context.long == False
    assert fake_context.quantity == 2


@pytest.mark.asyncio
async def test_on_new_price_close_with_exception(monkeypatch):
    with shelve.open(r'data_test\database_test') as db:
        for key in db.keys():
            fake_context: StrategyContext = db[key]
            break

    fake_context.position_units = 1
    fake_context.entry_prices = [Decimal(100)]
    fake_context.stop_levels = [Decimal(105)]

    price_in_point: Decimal = fake_context.breakout_level_short - fake_context.history_instrument.tick_size
    price_in_rub = (price_in_point / quotation_to_decimal(
        fake_context.history_instrument.instrument_info.min_price_increment)) * quotation_to_decimal(
        fake_context.history_instrument.instrument_info.min_price_increment_amount)
    quotation_price = decimal_to_quotation(price_in_rub)

    fake_order_state = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            average_position_price=ti.MoneyValue(
                currency='RUB',
                units=quotation_price.units,
                nano=quotation_price.nano,
            ),
            lots_executed=4,
            order_date='2022-01-01T00:00:00',
        )
    )
    update_strategy_context(fake_context, [fake_order_state], long=False)

    fake_order_state_close = s.fabrics_order_state(
        ti.OrderState(
            order_id='111',
            execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            average_position_price=ti.MoneyValue(
                currency='RUB',
                units=quotation_price.units,
                nano=quotation_price.nano,
            ),
            lots_executed=2,
            order_date='2022-01-01T00:00:00',
        )
    )

    monkeypatch.setattr('strategy.docnhian.order_for_close_position',
                        AsyncMock(return_value=[False]))

    fake_connect = ConnectTinkoff('TOKEN')

    price: Decimal = fake_context.stop_levels[-1] + Decimal(0.5)

    result = await fake_context.on_new_price(price=price, connect=fake_connect)

    assert fake_context.quantity == 4
    assert result == True
    assert isinstance(fake_context.state, TradeOpenState) == True
    assert len(fake_context.entry_prices) == 2
    assert fake_context.short == True
    assert fake_context.long == False
    assert fake_context.no_close == True

if __name__ == '__main__':
    pytest.main()
