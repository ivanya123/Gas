import asyncio
import datetime
import enum

import pandas as pd
import os

from tinkoff.invest import (
    AsyncClient,
    Quotation,
    CandleInterval,
    FuturesResponse,
    InstrumentStatus,
    Future, HistoricCandle, MarketDataRequest, SubscribeCandlesRequest, SubscriptionAction, CandleInstrument,
    SubscriptionInterval, SubscribeLastPriceRequest, LastPriceInstrument)
from tinkoff.invest.utils import now
from tinkoff.invest.async_services import AsyncMarketDataStreamManager

from function_processing import create_dict_row_from_response
from trad.obj import DataFutures


def string_to_interval(interval: str):
    dict_result = {
        '1m': CandleInterval.CANDLE_INTERVAL_1_MIN,
        '2m': CandleInterval.CANDLE_INTERVAL_2_MIN,
        '3m': CandleInterval.CANDLE_INTERVAL_3_MIN,
        '5m': CandleInterval.CANDLE_INTERVAL_5_MIN,
        '10m': CandleInterval.CANDLE_INTERVAL_10_MIN,
        '15m': CandleInterval.CANDLE_INTERVAL_15_MIN,
        '30m': CandleInterval.CANDLE_INTERVAL_30_MIN,
        '1h': CandleInterval.CANDLE_INTERVAL_HOUR,
        '2h': CandleInterval.CANDLE_INTERVAL_2_HOUR,
        '4h': CandleInterval.CANDLE_INTERVAL_4_HOUR,
        '1d': CandleInterval.CANDLE_INTERVAL_DAY,
        '1w': CandleInterval.CANDLE_INTERVAL_WEEK,
        '1M': CandleInterval.CANDLE_INTERVAL_MONTH
    }
    if interval in dict_result:
        return dict_result[interval]
    else:
        raise ValueError(f'Введите интервал в формате 1m, 2m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M')


class ConnectTinkoff:
    def __init__(self, token):
        self.token = token

    async def get_candles_from_ticker(self, ticker: str, interval: str) -> tuple[list[HistoricCandle], Future]:
        """
        Получение свечей по тикету
        :param ticker: str - Тикет инструмента
        :param interval: str - Интервал свечи в формате ('1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w', '1M')
        :return: list[HistoricCandle], Future - Список свечей и параметры фьючерса.
        """
        async with AsyncClient(self.token) as client:
            all_futures: FuturesResponse = await client.instruments.futures()
            instrument: Future = [x for x in all_futures.instruments if x.ticker == ticker][0]
            response: list[HistoricCandle] = []
            async for candle in client.get_all_candles(
                    instrument_id=instrument.uid,
                    to=instrument.expiration_date,
                    from_=instrument.expiration_date - datetime.timedelta(days=365),
                    interval=string_to_interval(interval)
            ):
                response.append(candle)
        return response, instrument

    async def connect(self):
        """
        Создаёт асинхронное соединение и инициализирует менеджер стриминга.
        """
        self._client = AsyncClient(self.token)
        self.client = await self._client.__aenter__()
        # Создаем market data stream через клиента.
        self.market_data_stream = self.client.create_market_data_stream()
        # Запускаем стриминг в фоне, чтобы получать сообщения
        self.listen = asyncio.create_task(self._listen_stream())

    async def _listen_stream(self) -> None:
        """
        Слушает сообщения из стриминга.
        """
        if self.market_data_stream is None:
            return
        if self.market_data_stream:
            async for msg in self.market_data_stream:
                print(msg)

    async def add_subscribe(self, instrument_id) -> None:
        """
        Добавляет подписку на свечи по id инструмента.
        :param instrument_id: str - Идентификатор инструмента.
        :return: None
        """
        if not self.market_data_stream:
            raise Exception("Не создан стриминг. Вызовите connect() сначала.")

        instrument = CandleInstrument(
            instrument_id=instrument_id,
            interval=SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE,
        )
        self.market_data_stream.candles.subscribe(instruments=[instrument])

    async def delete_subscribe(self, instrument_id):
        print(f'Удаляем подписку на свечи {instrument_id}')
        if not self.market_data_stream:
            raise Exception("Не создан стриминг. Вызовите connect() сначала.")

        instrument = CandleInstrument(
            instrument_id=instrument_id,
            interval=SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE,
        )
        self.market_data_stream.candles.unsubscribe(instruments=[instrument])

    async def disconnect(self):
        if self.market_data_stream:
            self.market_data_stream.stop()
            self.market_data_stream = None
            await self._client.__aexit__(None, None, None)




if __name__ == '__main__':
    from config import TOKEN


    async def main():
        connect = ConnectTinkoff(TOKEN)
        list_candles, instrument = await connect.get_candles_from_ticker('BMH5', '1h')
        await connect.connect()
        first = asyncio.create_task(connect.add_subscribe(instrument_id=instrument.uid))
        await first
        await asyncio.sleep(40)
        await asyncio.create_task(connect.delete_subscribe(instrument_id=instrument.uid))


        # await connect.disconnect()


    asyncio.run(main())
