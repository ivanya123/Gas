from tinkoff.invest import Quotation, Future, InstrumentIdType, Candle, OrderBook
from tinkoff.invest.async_services import AsyncServices
from tinkoff.invest.utils import quotation_to_decimal


def to_price(quotation: Quotation):
    quotation = abs(quotation)
    return quotation.units + quotation.nano / 1_000_000_000


async def get_increment_amount(client: AsyncServices, instrument_id: str) -> int:
    min_price_quatation = await client.instruments.get_futures_margin(instrument_id=instrument_id)
    return to_price(min_price_quatation.min_price_increment_amount)


async def get_instrument_info(client: AsyncServices, ticker: str, class_code: str) -> Future:
    return await client.instruments.future_by(class_code=class_code, id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                                              id=ticker)


def create_dict_from_candle(candle: Candle):
    return {
        'figi': candle.figi,
        'interval': candle.interval,
        'open': quotation_to_decimal(candle.open),
        'high': quotation_to_decimal(candle.high),
        'low': quotation_to_decimal(candle.low),
        'close': quotation_to_decimal(candle.close),
        'volume': candle.volume,
        'time_candle': candle.time,
        'last_trade_ts': candle.last_trade_ts,
        'instrument_uid': candle.instrument_uid,
    }


def create_dict_from_orderbook(orderbook: OrderBook):
    volume_order = sum([quotation_to_decimal(bids.price)*bids.quantity for bids in orderbook.bids])
    volume_asks = sum([quotation_to_decimal(asks.price)*asks.quantity for asks in orderbook.asks])
    return {
        'figi': orderbook.figi,
        'depth': orderbook.depth,
        'bids': orderbook.bids,
        'volume_order': volume_order,
        'asks': orderbook.asks,
        'volume_asks': volume_asks,
        'time_orderbook': orderbook.time,
        'limit_up': orderbook.limit_up,
        'limit_down': orderbook.limit_down,
        'instrument_uid': orderbook.instrument_uid,
    }


def create_dict_row_from_response(candle: Candle, orderbook: OrderBook) -> dict[str, str | int]:
    '''
    Создание словаря для записи в базу данных или файл из ответа по получение свечей и стакана при торговли!!
    :param candle: Candle - свеча
    :param orderbook: OrderBook - стакан к закрытию свечи.
    :return:
    '''
    candle_dict = create_dict_from_candle(candle)
    orderbook_dict = create_dict_from_orderbook(orderbook)
    return {**candle_dict, **orderbook_dict}


