from decimal import Decimal
import pickle as pkl

from trad.connect_tinkoff import ConnectTinkoff
from download_futers.historic_future import HistoricInstrument
import asyncio
from config import TOKEN

async def main():
    connect = ConnectTinkoff(TOKEN)
    list_candle, instrument = await connect.get_candles_from_ticker('BMH5', '1h')
    historic = HistoricInstrument(list_candle, instrument)
    historic.save_to_csv('historic', index=False)


if __name__ == '__main__':
    # asyncio.run(main())
    df = HistoricInstrument.from_csv('historic')
    print(df.info())






