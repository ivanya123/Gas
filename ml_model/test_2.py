"""Example - How to get figi by name of ticker."""
import logging
import os

from pandas import DataFrame

from tinkoff.invest import Client, SecurityTradingStatus
from tinkoff.invest.services import InstrumentsService
from tinkoff.invest.utils import quotation_to_decimal

from CONSTANTS import TOKEN


logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main():
    """Example - How to get figi by name of ticker."""

    ticker = "NGZ4"  # "BRH3" "SBER" "VTBR"

    with Client(TOKEN) as client:
        instruments: InstrumentsService = client.instruments
        tickers = []
        my_iter = instruments.futures().instruments
        for i in my_iter:
            tickers.append(i.class_code)
        print(set(tickers))


if __name__ == "__main__":
    main()
