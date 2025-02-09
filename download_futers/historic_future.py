import datetime
import pickle as pkl

import pandas as pd
import csv
import json

from tinkoff.invest import Future, HistoricCandle, MarketDataResponse, Quotation, MoneyValue
from tinkoff.invest.schemas import BrandData
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation


class HistoricInstrument:
    """
    Класс для сохранения и загрузки исторических данныхю
    """

    def __init__(self, instrument: Future, list_candles: list[HistoricCandle] = None, from_csv: bool = False,
                 path: str = '') -> None:
        """Конструктор класса
        :param list_candles: список исторических свечей
        :param instrument: объект класса Future - хранение основной информации об инструменте
        :param from_csv: флаг, если True, то данные будут загружаются из csv(реализуется в методе from_csv)"""

        df = []
        if not from_csv:
            for candle in list_candles:
                row = {
                    'time': candle.time,
                    'open': quotation_to_decimal(candle.open),
                    'high': quotation_to_decimal(candle.high),
                    'low': quotation_to_decimal(candle.low),
                    'close': quotation_to_decimal(candle.close),
                    'volume': candle.volume
                }
                df.append(row)
            self.data: pd.DataFrame = pd.DataFrame(df)
            self.instrument_info: Future = instrument
        else:
            if path:
                with open(path + '.pkl', 'r') as file:
                    self.instrument_info: Future = pkl.load(file)
                self.data: pd.DataFrame = pd.read_csv(path + '.csv')
                self.data['time'] = pd.to_datetime(self.data['time'])
            else:
                raise ValueError('path is empty')

    def save_to_csv(self, path: str, *args, **kwargs):
        """Сохранение данных в csv, json и pkl, принимает стандартные параметры для метода pd.DataFrame.to_csv
        :param path: путь к файлу (без расширения)"""
        pd.DataFrame.to_csv(self, path + '.csv', *args, **kwargs)
        with open(path + '.pkl', 'wb') as file:
            pkl.dump(self.instrument_info, file)
        instrument_dict = {}
        with open(path + '.json', 'w', encoding='utf-8') as file:
            for key, value in self.instrument_info.__dict__.items():
                if isinstance(value, Quotation):
                    instrument_dict[key] = float(quotation_to_decimal(value))
                if isinstance(value, datetime.datetime):
                    instrument_dict[key] = value.isoformat()
                if isinstance(value, MoneyValue):
                    instrument_dict[key] = value.__dict__
                if isinstance(value, BrandData):
                    instrument_dict[key] = value.__dict__
            json.dump(instrument_dict, file, indent=4)
