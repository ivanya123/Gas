from tinkoff.invest.sandbox.client import SandboxClient
import pprint

from CONSTANTS import TOKEN
import os

from tinkoff.invest import Client
from tinkoff.invest.services import InstrumentsService


def main():
    with Client(TOKEN) as client:
        pprint.pprint(client.users.get_info())
        instrument: InstrumentsService = client.instruments
        data = instrument.future_by(id_type=3, id='2f52fac0-36a0-4e7c-82f4-2f87beed762f')
        data_1 = instrument.get_futures_margin(instrument_id='2f52fac0-36a0-4e7c-82f4-2f87beed762f')
        pprint.pprint(data_1)
        # pprint.pprint(client.users.get_margin_attributes(account_id='2114726250'))


if __name__ == "__main__":
    main()
