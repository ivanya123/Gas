import os
import pandas as pd
import matplotlib.pyplot as plt

from data_proc import create_lag_features


def doncheana(col: pd.Series, hours: int = 20) -> list | pd.Series:
    list_data = col.tolist()
    max_list = col.tolist()
    min_list = col.tolist()
    for i in range(len(list_data)):
        if i < hours:
            max_list[i] = max(list_data[:i])
            min_list[i] = min(list_data[:i])
        else:
            max_list[i] = max(list_data[i-hours:i])
            min_list[i] = min(list_data[i-hours:i])
    return max_list, min_list





file_list = [pd.read_csv(x) for x in os.listdir() if x.endswith('.csv')]
for df in file_list:
    df['time'] = pd.to_datetime(df['time'])
    df['sma_close_30'] = df['close'].rolling(window=50).mean()
    df['sma_close_300'] = df['close'].rolling(window=200).mean()
    df['max_close'] = df['close'].rolling(window=20).max()
    df['min_close'] = df['close'].rolling(window=20).min()
    df['max_close_60'] = df['close'].rolling(window=60).max()
    df['min_close_60'] = df['close'].rolling(window=60).min()
    df['mean_doncheana_20'] = (df['max_close'] + df['min_close'])/2
    df['mean_doncheana_60'] = (df['max_close_60'] + df['min_close_60'])/2


    # Расчет параметров каналов Дончеана

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index[:], df.loc[:, 'close'])
    ax.plot(df.index[:], df.loc[:, 'max_close'], color='r')
    ax.plot(df.index[:], df.loc[:, 'min_close'], color='r')
    ax.plot(df.index[:], df.loc[:, 'mean_doncheana_20'], color='b')
    ax.plot(df.index[:], df.loc[:, 'max_close_60'], color='g')
    ax.plot(df.index[:], df.loc[:, 'min_close_60'], color='g')
    ax.plot(df.index[:], df.loc[:, 'mean_doncheana_60'], color='y')
    ax.legend(['close', 'max_close', 'min_close', 'mean_doncheana_20', 'max_close_60', 'min_close_60', 'mean_doncheana_60'])
    plt.show()
