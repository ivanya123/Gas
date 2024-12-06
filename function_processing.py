from tinkoff.invest import Quotation, Future, InstrumentIdType, Candle, OrderBook
from tinkoff.invest.async_services import AsyncServices


def to_price(quotation: Quotation):
    quotation = abs(quotation)
    return quotation.units + quotation.nano / 1_000_000_000


async def get_increment_amount(client: AsyncServices, instrument_id: str) -> int:
    min_price_quatation = await client.instruments.get_futures_margin(instrument_id=instrument_id)
    return to_price(min_price_quatation.min_price_increment_amount)


async def get_instrument_info(client: AsyncServices, ticker: str, class_code: str) -> Future:
    return await client.instruments.future_by(class_code=class_code, id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                                              id=ticker)


def create_dict_row_from_response(candle: Candle, orderbook: OrderBook) -> dict[str, str | int]:
    '''
    Создание словаря для записи в базу данных или файл из ответа по получение свечей и стакана при торговли!!
    :param candle: Candle - свеча
    :param orderbook: OrderBook - стакан к закрытию свечи.
    :return:
    '''
    pass

