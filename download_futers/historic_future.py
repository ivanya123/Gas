import datetime
import pickle as pkl

import pandas as pd
import json

from tinkoff.invest import Future, HistoricCandle, MarketDataResponse, Quotation, MoneyValue
from tinkoff.invest.schemas import BrandData
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation


class HistoricInstrument:
    """
    Класс для сохранения и загрузки исторических данныхю
    """

    def __init__(self, instrument: Future = None, list_candles: list[HistoricCandle] = None, from_csv: bool = False,
                 path: str = '') -> None:
        """Конструктор класса, вызывается либо с параметрами instriment, list_candles либо загружается из from_csv, path
        :param list_candles: список исторических свечей
        :param instrument: объект класса Future - хранение основной информации об инструменте
        :param from_csv: флаг, если True, то данные будут загружаются из csv"""

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
            self.time_last_candle: HistoricCandle = self.data.iloc[-1]['time']
        else:
            if path:
                with open(path + '.pkl', 'rb') as file:
                    self.instrument_info: Future = pkl.load(file)
                self.data: pd.DataFrame = pd.read_csv(path + '.csv')
                self.data['time'] = pd.to_datetime(self.data['time'])
                self.time_last_candle: pd.Timestamp = self.data.iloc[-1]['time']
            else:
                raise ValueError('path is empty')

    def save_to_csv(self, path: str, *args, **kwargs):
        """Сохранение данных в csv, json и pkl, принимает стандартные параметры для метода pd.DataFrame.to_csv
        :param path: путь к файлу (без расширения)"""
        self.data.to_csv(path + '.csv', *args, **kwargs)
        with open(path + '.pkl', 'wb') as file:
            pkl.dump(self.instrument_info, file)
        instrument_dict = {}
        with open(path + '.json', 'w', encoding='utf-8') as file:
            for key, value in self.instrument_info.__dict__.items():
                if isinstance(value, Quotation):
                    instrument_dict[key] = float(quotation_to_decimal(value))
                elif isinstance(value, datetime.datetime):
                    instrument_dict[key] = value.isoformat()
                elif isinstance(value, MoneyValue):
                    instrument_dict[key] = value.__dict__
                elif isinstance(value, BrandData):
                    instrument_dict[key] = value.__dict__
                else:
                    instrument_dict[key] = value
            json.dump(instrument_dict, file, indent=4)


    def create_donchian_canal(self, long_d:int, short_d:int):
        self.data[f'max_{long_d}_donchian'] = self.data['high'].rolling(long_d).max()
        self.data[f'min_{long_d}_donchian'] = self.data['low'].rolling(long_d).min()
        self.data[f'max_{short_d}_donchian'] = self.data['high'].rolling(short_d).max()
        self.data[f'min_{short_d}_donchian'] = self.data['low'].rolling(short_d).min()

        length_df = len(self.data)
        self.max_donchian = self.data.loc[length_df - 1, f'max_{long_d}_donchian']
        self.min_donchian = self.data.loc[length_df - 1, f'min_{long_d}_donchian']
        self.max_short_donchian = self.data.loc[length_df - 1, f'max_{short_d}_donchian']
        self.min_short_donchian = self.data.loc[length_df - 1, f'min_{short_d}_donchian']



    def __call__(self):
        return self.data, self.instrument_info
