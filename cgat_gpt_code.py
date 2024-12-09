import asyncio
import csv

from tinkoff.invest import (
    AsyncClient,
    MarketDataRequest,
    SubscribeCandlesRequest,
    SubscriptionAction,
    CandleInstrument,
    SubscriptionInterval,
    Quotation,
    InstrumentIdType, SubscribeOrderBookRequest, OrderBookInstrument, OrderBook, )

from CONSTANTS import TOKEN, CLASS_CODE
from function_processing import create_dict_row_from_response

TOKEN = TOKEN
FIGI = "FUTNG1224000"  # FIGI фьючерса
TICKER = "NGZ4"  # Тикер фьючерса
CLASS_CODE = "SPBFUT"  # Класс кода для фьючерсов на Мосбирже
UID = '2f52fac0-36a0-4e7c-82f4-2f87beed762f'


def to_price(quotation: Quotation) -> float:
    return quotation.units + quotation.nano / 1_000_000_000


async def get_increment_amount(client, instrument_id: str) -> float:
    response = await client.instruments.get_futures_margin(instrument_id=instrument_id)
    min_price_increment_amount = response.min_price_increment_amount
    if min_price_increment_amount is None:
        raise ValueError("min_price_increment_amount отсутствует.")
    return to_price(min_price_increment_amount)


async def get_instrument_info(client, ticker: str, class_code: str):
    response = await client.instruments.future_by(
        id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
        class_code=class_code,
        id=ticker
    )
    return response.instrument


async def periodic_increment_amount_update(client, instrument_id, update_interval, shared_data, lock):
    while True:
        try:
            new_increment_amount = await get_increment_amount(client, instrument_id)
            async with lock:
                shared_data['min_price_amount'] = new_increment_amount
            print(f"Обновлено min_price_amount: {new_increment_amount}")
        except Exception as e:
            print(f"Ошибка при обновлении min_price_amount: {e}")
        await asyncio.sleep(update_interval)


async def main():
    # Общие данные и блокировка
    shared_data = {}
    lock = asyncio.Lock()

    async def request_iterator():
        # Сначала подписка на свечи
        yield MarketDataRequest(
            subscribe_candles_request=SubscribeCandlesRequest(
                subscription_action=SubscriptionAction.SUBSCRIPTION_ACTION_SUBSCRIBE,
                waiting_close=True,
                instruments=[
                    CandleInstrument(figi=FIGI, interval=SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE)]
            )
        )
        # Затем подписка на стакан
        yield MarketDataRequest(
            subscribe_order_book_request=SubscribeOrderBookRequest(
                subscription_action=SubscriptionAction.SUBSCRIPTION_ACTION_SUBSCRIBE,
                instruments=[OrderBookInstrument(figi=FIGI, depth=40, instrument_id=UID)]
            )
        )
        while True:
            await asyncio.sleep(1)

    async with AsyncClient(TOKEN) as client:
        # Инициализируем min_price_amount
        min_price_amount = await get_increment_amount(client, FIGI)
        shared_data['min_price_amount'] = min_price_amount

        # Получаем min_increment
        min_increment_response = await client.instruments.get_futures_margin(figi=FIGI)
        min_increment = to_price(min_increment_response.min_price_increment)

        # Получаем информацию о фьючерсе
        futures = await get_instrument_info(client, TICKER, CLASS_CODE)

        # Запускаем задачу периодического обновления min_price_amount
        update_interval = 300  # Обновляем каждые 5 минут (в секундах)
        update_task = asyncio.create_task(
            periodic_increment_amount_update(client, FIGI, update_interval, shared_data, lock)
        )

        # Открываем CSV файл для записи данных
        with open('futures_price_data.csv', mode='w', newline='') as csv_file:

            first_iteration = True
            orderbook = None
            async for marketdata in client.market_data_stream.market_data_stream(
                    request_iterator()
            ):
                if marketdata.orderbook:
                    orderbook: OrderBook = marketdata.orderbook

                if candle := marketdata.candle:
                    # Получаем актуальное значение min_price_amount


                    async with lock:
                        current_min_price_amount = shared_data['min_price_amount']

                    dict_row = create_dict_row_from_response(candle, orderbook)
                    if first_iteration:
                        first_iteration = False
                        writer = csv.DictWriter(csv_file, fieldnames=dict_row.keys())


                    # Записываем данные в CSV файл
                    writer.writerow(dict_row)
                    print(dict_row)


        # Отменяем задачу обновления при завершении
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
