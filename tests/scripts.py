import shelve
from decimal import Decimal

import tinkoff.invest as ti
from tinkoff.invest import _grpc_helpers
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation, money_to_decimal

from strategy.docnhian import StrategyContext


class FakeAsyncServices:
    def __init__(self):
        self.orders = Orders()


def fabrics_money_value(price: float) -> ti.MoneyValue:
    currency = 'RUB'
    price_dec = Decimal(price)
    units = price_dec // 1
    nano = Decimal((price_dec - units) * 1_000_000_000)
    return ti.MoneyValue(currency=currency, units=units, nano=nano)


def fabrics_order_state(order_state: ti.OrderState) -> ti.OrderState:
    for key, value in order_state.__dict__.items():
        if type(value) == object:
            order_state.__dict__[key] = None
    return order_state


def fabrics_post_order_response(post_order_response: ti.PostOrderResponse) -> ti.PostOrderResponse:
    for key, value in post_order_response.__dict__.items():
        if type(value) == object:
            post_order_response.__dict__[key] = None
    return post_order_response


def fabrics_order_trades(order_trades: ti.OrderTrades) -> ti.OrderTrades:
    for key, value in order_trades.__dict__.items():
        if type(value) == object:
            order_trades.__dict__[key] = None
    return order_trades


class Orders:
    def get_order_state(self):
        return 0

    def cancel_order(self):
        return 0


if __name__ == '__main__':
    order_state: ti.OrderState = ti.OrderState(
        order_id='13564817835',
        execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_PARTIALLYFILL,
        lots_requested=10,
        lots_executed=10,
        initial_order_price=fabrics_money_value(3000.5),
        executed_order_price=fabrics_money_value(3000.5),
        total_order_amount=fabrics_money_value(3000.5 * 10),
        average_position_price=fabrics_money_value(3000.5),
        initial_commission=fabrics_money_value(0.01),
        executed_commission=fabrics_money_value(0.01),
        figi='',
        direction=ti.OrderDirection.ORDER_DIRECTION_BUY,
        initial_security_price=fabrics_money_value(3000.5),
        stages=[ti.OrderStage(price=fabrics_money_value(3000.5),
                              quantity=10,
                              trade_id='123',
                              execution_time='123')],
        service_commission=fabrics_money_value(0.01),
        currency='RUB',
        order_type=ti.OrderType.ORDER_TYPE_LIMIT,
        order_date='123',
        instrument_uid='123',
        order_request_id='123'
    )
    small_order_state: ti.OrderState = ti.OrderState(
        order_id='13564817835',
        execution_report_status=ti.OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_PARTIALLYFILL,
    )

    with shelve.open(r'C:\Users\aples\PycharmProjects\Gas\data_strategy_state\dict_strategy_state') as db:
        for key in db.keys():
            fake_context: StrategyContext = db[key]
            break

    with shelve.open(r'data_test/database_test') as db:
        db['context'] = fake_context
