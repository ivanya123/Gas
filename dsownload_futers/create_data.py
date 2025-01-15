import os

import matplotlib.pyplot as plt
import pandas as pd

from data_proc import create_lag_features

file_list = [pd.read_csv(x) for x in os.listdir() if x.endswith('.csv')]
for df in file_list:
    df['time'] = pd.to_datetime(df['time'])
    df['sma_close_30'] = df['close'].rolling(window=30).mean()
    df['sma_close_200'] = df['close'].rolling(window=200).mean()
    df['max_close'] = df['close'].rolling(window=20).max()
    df['min_close'] = df['close'].rolling(window=20).min()
    df['max_close_60'] = df['close'].rolling(window=60).max()
    df['min_close_60'] = df['close'].rolling(window=60).min()
    df['mean_doncheana_20'] = (df['max_close'] + df['min_close']) / 2
    df['mean_doncheana_60'] = (df['max_close_60'] + df['min_close_60']) / 2
    df, new_columns = create_lag_features(df, backward_lags=30, columns=['close'], forward_lags=None)
    df['future_mean_price'] = df[new_columns].mean(axis=1)
    df['percent_change'] = ((df['future_mean_price'] - df['close']) / df['close']) * 100
    df, max_new_columns = create_lag_features(df, backward_lags=30, columns=['high'], forward_lags=None)
    df, min_new_columns = create_lag_features(df, backward_lags=30, columns=['low'], forward_lags=None)
    df['max_price_future_5'] = df[max_new_columns[:5]].max(axis=1)
    df['percent_max_price_future'] = ((df['max_price_future_5'] - df['close']) / df['close']) * 100
    df['min_price_future_5'] = df[min_new_columns[:5]].min(axis=1)
    df['percent_min_price_future'] = ((df['min_price_future_5'] - df['close']) / df['close']) * 100
    df['volatility_30'] = df[new_columns].std(axis=1)
    df['month'] = df['time'].dt.month
    df['day'] = df['time'].dt.day

    # Расчет параметров каналов Дончеана

    fig, ax = plt.subplots(figsize=(10, 5))
    ax_2 = ax.twinx()
    ax.plot(df.index[:], df.loc[:, 'close'])
    # ax.plot(df.index[:], df.loc[:, 'max_close'], color='r')
    # ax.plot(df.index[:], df.loc[:, 'min_close'], color='r')
    # ax.plot(df.index[:], df.loc[:, 'mean_doncheana_20'], color='b')
    # ax.plot(df.index[:], df.loc[:, 'max_close_60'], color='g')
    # ax.plot(df.index[:], df.loc[:, 'min_close_60'], color='g')
    # ax.plot(df.index[:], df.loc[:, 'mean_doncheana_60'], color='y')
    # ax.plot(df.index[:], df.loc[:, 'future_mean_price'])
    # ax_2.plot(df.index[:], df.loc[:, 'percent_max_price_future'], color='g', label = 'max_price_future_5')
    # ax_2.plot(df.index[:], df.loc[:, 'percent_min_price_future'], color='r', label = 'min_price_future_5')
    # ax_2.plot(df.index[:], df.loc[:, 'volatility_30'], color='k', label = 'volatility_30')
    # ax.legend(['close', 'future_mean_price'])
    plt.show()


def create_dataframe_for_learning(df: pd.DataFrame, length_short_sma: int = 30, length_long_sma: int = 200,
                                  short_donchian_parameters: int = 20, long_donchian_parameters: int = 200):
    df['time'] = pd.to_datetime(df['time'])
    df[f'sma_close_{length_short_sma}'] = df['close'].rolling(length_short_sma).mean()
    df[f'sma_close_{length_long_sma}'] = df['close'].rolling(length_long_sma).mean()
    df[f'max_donchian_close_{short_donchian_parameters}'] = df['close'].rolling(short_donchian_parameters).max()
    df[f'min_donchian_close_{short_donchian_parameters}'] = df['close'].rolling(short_donchian_parameters).min()
    df[f'max_donchian_close_{long_donchian_parameters}'] = df['close'].rolling(long_donchian_parameters).max()
    df[f'min_donchian_close_{long_donchian_parameters}'] = df['close'].rolling(long_donchian_parameters).min()
    df[f'mean_donchian_close_{short_donchian_parameters}'] = (df[f'max_donchian_close_{short_donchian_parameters}'] -
                                                              df[f'min_donchian_close_{short_donchian_parameters}']) / 2
    df[f'mean_donchian_close_{long_donchian_parameters}'] = (df[f'max_donchian_close_{long_donchian_parameters}'] -
                                                             df[f'min_donchian_close_{long_donchian_parameters}']) / 2

    # Добавление target признаков.

