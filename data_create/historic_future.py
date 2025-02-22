import datetime
import json
import pickle as pkl

import pandas as pd
from tinkoff.invest import Future, HistoricCandle, Quotation, MoneyValue
from tinkoff.invest.schemas import BrandData
from tinkoff.invest.utils import quotation_to_decimal


class HistoricInstrument:
    """
    Класс для сохранения и загрузки исторических данныхю
    """

    def __init__(self, instrument: Future = None, list_candles: list[HistoricCandle] = None) -> None:
        """Конструктор класса, вызывается либо с параметрами instriment, list_candles либо загружается из from_csv, path
        :param list_candles: список исторических свечей
        :param instrument: объект класса Future - хранение основной информации об инструменте"""

        df = []

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
        self.tick_size = quotation_to_decimal(self.instrument_info.min_price_increment_amount)
        self.atr = self.create_atr()

    def create_atr(self, n=14) -> float:
        # Добавляем столбец с предыдущим close
        self.data['prev_close'] = self.data['close'].shift(1)

        # Вычисляем True Range (TR) для каждой свечи:
        # Если предыдущего close нет, используем high - low.
        self.data['tr'] = self.data.apply(
            lambda row: max(
                row['high'] - row['low'],
                abs(row['high'] - row['prev_close']) if pd.notnull(row['prev_close']) else 0,
                abs(row['low'] - row['prev_close']) if pd.notnull(row['prev_close']) else 0
            ),
            axis=1
        )

        # Вычисляем ATR как скользящее среднее по TR за n периодов (можно задать min_periods=1 для первых строк)
        atr = self.data['tr'].rolling(window=n, min_periods=1).mean().iloc[-1]

        return atr

    def save_to_csv(self, path: str, *args, **kwargs):
        """Сохранение данных в csv, json и pkl, принимает стандартные параметры для метода pd.DataFrame.to_csv
        :param path: путь к файлу (без расширения)"""
        self.data.to_csv(path + '.csv', *args, **kwargs)
        with open(path + '.pkl', 'wb') as file:
            # pkl.dump(self.instrument_info, file)
            pkl.dump(self, file)
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

    def create_donchian_canal(self, long_d: int, short_d: int):
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

    @classmethod
    def from_pkl(cls, path: str):
        """Загрузка данных из csv, json и pkl, принимает стандартные параметры для метода pd.DataFrame.to_csv
        :param path: путь к файлу (без расширения)"""
        with open(path + '.pkl', 'rb') as file:
            return pkl.load(file)
