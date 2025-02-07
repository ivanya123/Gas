import csv
import pandas as pd


class DataFutures(pd.DataFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(self) > 0:
            self.last_candles = self.loc[len(self) - 1, :]
            self.last_time = self.last_candles['time']
        else:
            self.last_time = None
            self.last_candles = None

    def update_data(self, candles: dict[str, float] = None):
        if len(self) > 0:
            if candles is not None:
                if candles['time'] > self.last_time:
                    self.loc[len(self)] = candles
                    self.last_time = candles['time']
                    self.last_candles = self.loc[len(self) - 1, :]
            else:
                self.last_candles = self.loc[len(self) - 1, :]
                self.last_time = self.last_candles['time']

    @classmethod
    def from_csv(cls, csv_file: str):
        with open(csv_file) as f:
            k = csv.DictReader(f)
            list_candles = []
            for row in k:
                list_candles.append(row)

        df = cls(list_candles)
        df['time'] = pd.to_datetime(df['time'])
        df.update_data()
        return df


if __name__ == "__main__":
    df = pd.DataFrame([{1: 's', 2: 'e'}, {1: 'q', 2: 'w'}])
    df_ = DataFutures.from_csv(r'C:\Users\aples\PycharmProjects\Gas\download_futers\NGF2.csv')
    print(type(df_.last_time))
