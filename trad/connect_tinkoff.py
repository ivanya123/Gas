import asyncio
import datetime
import json

from async_lru import alru_cache
from tinkoff.invest import (
    AsyncClient,
    CandleInterval,
    FuturesResponse,
    Future, HistoricCandle, CandleInstrument,
    SubscriptionInterval, LastPriceInstrument, GetAccountsResponse,
    PortfolioResponse, FutureResponse, InfoInstrument, InstrumentIdType, InstrumentResponse, Quotation, OrderDirection,
    OrderType)
from tinkoff.invest.async_services import AsyncServices
from tinkoff.invest.market_data_stream.async_market_data_stream_manager import AsyncMarketDataStreamManager


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
        self.queue_order: asyncio.Queue = asyncio.Queue()
        self.token = token
        self.queue: asyncio.Queue | None = None
        self.queue_portfolio: asyncio.Queue | None = None
        self.queue_operations: asyncio.Queue | None = None
        self.market_data_stream: AsyncMarketDataStreamManager | None = None
        self.listen: asyncio.Task | None = None
        self.client: AsyncServices | None = None
        self._client: AsyncClient | None = None

    async def connect(self):
        """
        Создаёт асинхронное соединение и инициализирует менеджер стриминга.
        """
        self._client = AsyncClient(self.token)
        self.client = await self._client.__aenter__()
        self.market_data_stream: AsyncMarketDataStreamManager = self.client.create_market_data_stream()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.listen: asyncio.Task = asyncio.create_task(self._listen_stream())

    async def _listen_stream(self) -> None:
        """
        Слушает сообщения из стриминга.
        """

        if self.market_data_stream is None:
            return
        while True:
            try:
                async for msg in self.market_data_stream:
                    print('Все норм')
                    await self.queue.put(msg)
            except Exception as e:
                print(f'Ошибка при получении сообщения: {e}')
                await self.queue.put(e)
                await asyncio.sleep(5)
                self.market_data_stream = self.client.create_market_data_stream()

    async def get_candles_from_ticker(self, ticker: str, interval: str) -> tuple[list[HistoricCandle], Future]:
        """
        Получение свечей по тикету
        :param ticker: str - Тикет инструмента
        :param interval: str - Интервал свечи в формате ('1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w', '1M')
        :return: list[HistoricCandle], Future - Список свечей и параметры фьючерса.
        """

        all_futures: FuturesResponse = await self.client.instruments.futures()
        instrument: Future = [x for x in all_futures.instruments if x.ticker == ticker][0]
        response: list[HistoricCandle] = []
        now = datetime.datetime.now(datetime.timezone.utc)
        async for candle in self.client.get_all_candles(
                instrument_id=instrument.uid,
                to=now + datetime.timedelta(days=1),
                from_=now - datetime.timedelta(days=365),
                interval=string_to_interval(interval)
        ):
            response.append(candle)
        return response, instrument

    async def get_candles_from_uid(self, uid: str, interval: str | None = None) -> tuple[list[HistoricCandle], Future]:
        instrument: FutureResponse = await self.client.instruments.future_by(id=uid, id_type=3)
        now = datetime.datetime.now(datetime.timezone.utc)
        response: list[HistoricCandle] = []
        if interval is None:
            interval = '1m'
        async for candle in self.client.get_all_candles(
                instrument_id=instrument.instrument.uid,
                to=now + datetime.timedelta(days=1),
                from_=now - datetime.timedelta(days=365),
                interval=string_to_interval(interval)
        ):
            response.append(candle)
        return response, instrument.instrument

    @alru_cache
    async def figi_to_name(self, figi: str) -> str:
        if self.client:
            instrument: InstrumentResponse = await self.client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            )
            if instrument:
                with open('figi_to_name.json', 'r') as f:
                    figi_to_name = json.load(f)
                if instrument.instrument.figi not in figi_to_name:
                    figi_to_name[instrument.instrument.figi] = instrument.instrument.name
                    with open('figi_to_name.json', 'w') as f:
                        json.dump(figi_to_name, f, indent=4)
                return instrument.instrument.name

    async def add_subscribe_candle(self, instruments: list[str], interval: str | None = None) -> None:
        """
        Добавляет подписку на свечи по id инструмента.
        :param instruments: str - Список id инструментов.
        :param interval: str - Возможные интервалы стрима - "1m", "5m" or SUBSCRIPTION_INTERVAL_UNSPECIFIED
        :return: None
        """

        dict_subscription_interval = {
            '1m': SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE,
            '5m': SubscriptionInterval.SUBSCRIPTION_INTERVAL_FIVE_MINUTES
        }
        if interval is None:
            interval = 'SUBSCRIPTION_INTERVAL_UNSPECIFIED'
        if not self.market_data_stream:
            raise Exception("Не создан стриминг. Вызовите connect() сначала.")

        instruments: list[CandleInstrument] = [CandleInstrument(
            instrument_id=instrument_id,
            interval=dict_subscription_interval.get(interval,
                                                    SubscriptionInterval.SUBSCRIPTION_INTERVAL_UNSPECIFIED)
        ) for instrument_id in instruments]
        self.market_data_stream.candles.subscribe(instruments=instruments)

    async def add_subscribe_last_price(self, instruments: list[str]) -> None:
        """
        Добавляет подписку на цены последних сделок по id инструментов.
        :param instruments: str - Список id инструментов.
        :return: None
        """
        if not self.market_data_stream:
            raise Exception("Не создан стриминг. Вызовите connect() сначала.")

        instruments: list[LastPriceInstrument] = [LastPriceInstrument(instrument_id=instrument_id) for instrument_id
                                                  in
                                                  instruments]

        self.market_data_stream.last_price.subscribe(instruments=instruments)

    async def add_subscribe_status_instrument(self, instruments_id: list[str]) -> None:
        """
        Добавляет подписку на статус инструмента
        :param instruments_id: список id инструментов
        :return:
        """
        if not self.market_data_stream:
            raise Exception("Не создан стриминг. Вызовите connect() сначала.")

        instruments = [InfoInstrument(instrument_id=instrument_id) for instrument_id in instruments_id]
        self.market_data_stream.info.subscribe(instruments=instruments)

    async def delete_subscribe(self, instrument_id, last_price: bool = False):
        """
        Удаляем подписку на свечи по инструменту
        :param instrument_id: id инструмента
        :param last_price: bool - Удаляем цену на последние цены сделок.
        :return:
        """
        print(f'Удаляем подписку на свечи {instrument_id}')
        if not self.market_data_stream:
            raise Exception("Не создан стриминг. Вызовите connect() сначала.")

        if not last_price:
            instrument = CandleInstrument(
                instrument_id=instrument_id,
                interval=SubscriptionInterval.SUBSCRIPTION_INTERVAL_ONE_MINUTE,
            )
            self.market_data_stream.candles.unsubscribe(instruments=[instrument])
        else:
            instrument = LastPriceInstrument(instrument_id=instrument_id)
            self.market_data_stream.last_price.unsubscribe(instruments=[instrument])

    async def info_accounts(self) -> list[PortfolioResponse]:
        """
        Получение информации о портфеле
        :return:
        """

        if self.client:
            accounts: GetAccountsResponse = await self.client.users.get_accounts()
            acc: list[PortfolioResponse] = []
            for account in accounts.accounts:
                portfolio_data: PortfolioResponse = await self.client.operations.get_portfolio(
                    account_id=account.id)
                acc.append(portfolio_data)
            return acc

    async def get_portfolio_by_id(self, account_id: str) -> PortfolioResponse:
        """
        Получение информации о портфеле
        :return:
        """
        if self.client:
            portfolio_data: PortfolioResponse = await self.client.operations.get_portfolio(
                account_id=account_id)
            return portfolio_data

    async def listening_portfolio_by_id(self, account_id: str):
        """
        Подписка на стрим для прослушивания динамической информации оь изменении портфеля
        :return:
        """
        if not self.queue_portfolio:
            self.queue_portfolio = asyncio.Queue()
        async for portfolio_response in self.client.operations_stream.portfolio_stream(
                accounts=[account_id]):
            self.queue_portfolio.put_nowait(portfolio_response)

    async def listening_operations_by_id(self, account_id: str):
        """
        Подписка и прослушивание стрима операций(сделок) портфеля.
        :param account_id:
        :return: None
        """
        if not self.queue_portfolio:
            self.queue_portfolio = asyncio.Queue()
        async for operations_response in self.client.operations_stream.positions_stream(
                accounts=[account_id]):
            self.queue_portfolio.put_nowait(operations_response)

    async def post_order(self, instrument_id: str, quantity: int, price: Quotation, direction: OrderDirection,
                         account_id: str, order_id: str, order_type: OrderType):
        if client := self.client:
            kwargs = {
                'instrument_id': instrument_id,
                'quantity': quantity,
                'price': price,
                'direction': direction,
                'account_id': account_id,
                'order_id': order_id,
                'order_type': order_type
            }
            result = await client.orders.post_order(**kwargs)
            self.queue_order.put_nowait(result)
            return result

    async def disconnect(self):
        if self.market_data_stream:
            self.market_data_stream.stop()
            self.market_data_stream = None
            await self._client.__aexit__(None, None, None)


if __name__ == '__main__':
    from config import TOKEN

    connect = ConnectTinkoff(TOKEN)


    async def main():
        pass


    asyncio.run(main())
