import os
from enum import Enum

import matplotlib.pyplot as plt
import pandas as pd

from data_proc import create_lag_features


# file_list = [pd.read_csv(x) for x in os.listdir() if x.endswith('.csv')]
# for df in file_list:
#     df['time'] = pd.to_datetime(df['time'])
#     df['sma_close_30'] = df['close'].rolling(window=30).mean()
#     df['sma_close_200'] = df['close'].rolling(window=200).mean()
#     df['max_close'] = df['close'].rolling(window=20).max()
#     df['min_close'] = df['close'].rolling(window=20).min()
#     df['max_close_60'] = df['close'].rolling(window=60).max()
#     df['min_close_60'] = df['close'].rolling(window=60).min()
#     df['mean_doncheana_20'] = (df['max_close'] + df['min_close']) / 2
#     df['mean_doncheana_60'] = (df['max_close_60'] + df['min_close_60']) / 2
#     df, new_columns = create_lag_features(df, backward_lags=30, columns=['close'], forward_lags=None)
#     df['future_mean_price'] = df[new_columns].mean(axis=1)
#     df['percent_change'] = ((df['future_mean_price'] - df['close']) / df['close']) * 100
#     df, max_new_columns = create_lag_features(df, backward_lags=30, columns=['high'], forward_lags=None)
#     df, min_new_columns = create_lag_features(df, backward_lags=30, columns=['low'], forward_lags=None)
#     df['max_price_future_5'] = df[max_new_columns[:5]].max(axis=1)
#     df['percent_max_price_future'] = ((df['max_price_future_5'] - df['close']) / df['close']) * 100
#     df['min_price_future_5'] = df[min_new_columns[:5]].min(axis=1)
#     df['percent_min_price_future'] = ((df['min_price_future_5'] - df['close']) / df['close']) * 100
#     df['volatility_30'] = df[new_columns].std(axis=1)
#     df['month'] = df['time'].dt.month
#     df['day'] = df['time'].dt.day
#
#     # Расчет параметров каналов Дончеана
#
#     fig, ax = plt.subplots(figsize=(10, 5))
#     ax_2 = ax.twinx()
#     ax.plot(df.index[:], df.loc[:, 'close'])
#     # ax.plot(df.index[:], df.loc[:, 'max_close'], color='r')
#     # ax.plot(df.index[:], df.loc[:, 'min_close'], color='r')
#     # ax.plot(df.index[:], df.loc[:, 'mean_doncheana_20'], color='b')
#     # ax.plot(df.index[:], df.loc[:, 'max_close_60'], color='g')
#     # ax.plot(df.index[:], df.loc[:, 'min_close_60'], color='g')
#     # ax.plot(df.index[:], df.loc[:, 'mean_doncheana_60'], color='y')
#     # ax.plot(df.index[:], df.loc[:, 'future_mean_price'])
#     # ax_2.plot(df.index[:], df.loc[:, 'percent_max_price_future'], color='g', label = 'max_price_future_5')
#     # ax_2.plot(df.index[:], df.loc[:, 'percent_min_price_future'], color='r', label = 'min_price_future_5')
#     # ax_2.plot(df.index[:], df.loc[:, 'volatility_30'], color='k', label = 'volatility_30')
#     # ax.legend(['close', 'future_mean_price'])
#     plt.show()


class EvalParameter(Enum):
    CLOSE = 'close'
    HIGH = 'high'
    LOW = 'low'
    OPEN = 'open'
    VOLUME = 'volume'


def create_dataframe_for_learning(df: pd.DataFrame,
                                  sma_period_small: int = 30,
                                  sma_period_long: int = 200,
                                  donchian_period_small: int = 20,
                                  donchian_period_long: int = 200,
                                  evaluation_parameter: EvalParameter = EvalParameter.CLOSE.value,
                                  period_mean_price_target: int = 10,
                                  period_max_price_target: int = 5) -> tuple[pd.DataFrame, list[str], list[str]]:
    '''
    Функция для создания датафрейма для обучения модели.
    :param df: Датафрейм с данными часовых свеч по фьючерсу
    :param sma_period_small: Длина короткой скользящей средней
    :param sma_period_long: Длина длинной скользящей средней
    :param donchian_period_small: Параметр показывающей период короткого канала Дончяна
    :param donchian_period_long: Параметр показывающей период длинного канала Дончяна
    :param evaluation_parameter: По какому столбцу считать параметры.
    :return: Датафрейм с данными для обучения модели, список столбцов парметров, список столбцов целевого признака
    '''
    l_columns: list[str] = [f'sma_close_{sma_period_small}',
                            f'sma_close_{sma_period_long}',
                            f'max_donchian_close_{donchian_period_small}',
                            f'min_donchian_close_{donchian_period_small}',
                            f'max_donchian_close_{donchian_period_long}',
                            f'min_donchian_close_{donchian_period_long}',
                            f'mean_donchian_close_{donchian_period_small}',
                            f'mean_donchian_close_{donchian_period_long}',
                            'close',
                            'high',
                            'low',
                            'volume',
                            'time']
    df['time'] = pd.to_datetime(df['time'])
    df[f'sma_close_{sma_period_small}'] = df[f'{evaluation_parameter}'].rolling(sma_period_small).mean()
    df[f'sma_close_{sma_period_long}'] = df[f'{evaluation_parameter}'].rolling(sma_period_long).mean()
    df[f'max_donchian_{donchian_period_small}'] = (
        df[f'{EvalParameter.HIGH.value}'].rolling(donchian_period_small).max()
    )

    df[f'min_donchian_{donchian_period_small}'] = (
        df[f'{EvalParameter.LOW.value}'].rolling(donchian_period_small).min()
    )

    df[f'max_donchian_close_{donchian_period_long}'] = (
        df[f'{EvalParameter.HIGH.value}'].rolling(donchian_period_long).max()
    )

    df[f'min_donchian_close_{donchian_period_long}'] = (
        df[f'{EvalParameter.LOW.value}'].rolling(donchian_period_long).min()
    )

    df[f'mean_donchian_close_{donchian_period_small}'] = (df[f'max_donchian_close_{donchian_period_small}'] -
                                                          df[f'min_donchian_close_{donchian_period_small}']) / 2

    df[f'mean_donchian_close_{donchian_period_long}'] = (df[f'max_donchian_close_{donchian_period_long}'] -
                                                         df[f'min_donchian_close_{donchian_period_long}']) / 2

    # Создание столбцов с предыдущими значениями свечей.
    df, learning_columns = create_lag_features(df,
                                               columns=l_columns,
                                               forward_lags=15,
                                               backward_lags=None)

    # Добавление target признаков.
    # Процент изменения цены за period_mean_price_target дней.
    df, columns_future = create_lag_features(df,
                                             columns=[f'{evaluation_parameter}'],
                                             backward_lags=period_mean_price_target,
                                             forward_lags=None)
    df[f'future_mean_price_{period_mean_price_target}'] = df[columns_future].mean(axis=1)

    df[f'percent_change_{period_mean_price_target}'] = (
            ((df[f'future_mean_price_{period_mean_price_target}'] -
              df[f'{evaluation_parameter}']) / df[f'{evaluation_parameter}']) * 100
    )
    # Показзывает максимум и минимум изменение цены за period_max_price_target дней.
    df, max_new_columns = create_lag_features(df,
                                              columns=[f'{EvalParameter.HIGH.value}'],
                                              backward_lags=period_max_price_target,
                                              forward_lags=None
                                              )
    df, min_new_columns = create_lag_features(df,
                                              columns=[f'{EvalParameter.LOW.value}'],
                                              backward_lags=period_max_price_target,
                                              forward_lags=None
                                              )
    df[f'max_price_future_{period_max_price_target}'] = df[max_new_columns].max(axis=1)
    df[f'percent_max_price_future_{period_max_price_target}'] = (
            ((df[f'max_price_future_{period_max_price_target}'] -
              df[f'{evaluation_parameter}']) / df[f'{evaluation_parameter}']) * 100
    )
    df[f'min_price_future_{period_max_price_target}'] = df[min_new_columns].min(axis=1)
    df[f'percent_min_price_future_{period_max_price_target}'] = (
            ((df[f'min_price_future_{period_max_price_target}'] -
              df[f'{evaluation_parameter}']) / df[f'{evaluation_parameter}']) * 100
    )
    df = df.drop(max_new_columns, axis=1)
    df = df.drop(min_new_columns, axis=1)

    # Показатель волатильности в следующие period_mean_price_target дней.
    df[f'volatility_{period_mean_price_target}_future'] = df[columns_future].std(axis=1)

    df = df.drop(columns_future, axis=1)
    # Показатели даты
    df['day'] = df['time'].dt.day
    df['month'] = df['time'].dt.month

    l_columns.extend(learning_columns)
    target_columns: list[str] = [f'percent_max_price_future_{period_max_price_target}',
                                 f'percent_min_price_future_{period_max_price_target}',
                                 f'volatility_{period_mean_price_target}_future',
                                 f'percent_change_{period_mean_price_target}']
    return df, l_columns, target_columns


def realization_strategy_donchian(df: pd.DataFrame,
                                  donchian_period: int,
                                  sma_period: int,
                                  profit: float,
                                  loss: float,
                                  vizualisation: bool = False) -> pd.DataFrame:
    """
    Реализация стратегии Дончиана с визуализацией и учётом сделок.

    :param df: DataFrame с данными (должен содержать 'close', 'high', 'low').
    :param donchian_period: Период канала Дончиана.
    :param sma_period: Период скользящей средней (для фильтрации).
    :param profit: Тейк-профит (в процентах, например, 0.02 для 2%).
    :param loss: Стоп-лосс (в процентах, например, 0.01 для 1%).
    :return: DataFrame с добавленными сделками и результатами.
    """
    df = df.copy()

    # Расчёт границ канала Дончиана и SMA
    df[f'donchian_max_{donchian_period}'] = df['high'].rolling(donchian_period).max().shift(1)
    df[f'donchian_min_{donchian_period}'] = df['low'].rolling(donchian_period).min().shift(1)
    df[f'sma_{sma_period}'] = df['close'].rolling(sma_period).mean()

    # Сигналы на вход
    df['long_entry'] = (df['close'] > df[f'donchian_max_{donchian_period}']) & (df['close'] > df[f'sma_{sma_period}'])
    df['short_entry'] = (df['close'] < df[f'donchian_min_{donchian_period}']) & (df['close'] < df[f'sma_{sma_period}'])

    # Визуализация
    if vizualisation:
        fig, ax = plt.subplots(figsize=(17, 12))
        ax.plot(df.index, df['close'], label='Close')
        ax.plot(df.index, df[f'donchian_max_{donchian_period}'], color='r', label=f'Donchian Max ({donchian_period})')
        ax.plot(df.index, df[f'donchian_min_{donchian_period}'], color='g', label=f'Donchian Min ({donchian_period})')

        # Добавляем точки входа
        ax.scatter(df.index[df['long_entry']], df.loc[df['long_entry'], 'close'], color='blue', label='Long Entry')
        ax.scatter(df.index[df['short_entry']], df.loc[df['short_entry'], 'close'], color='orange', label='Short Entry')

        ax.legend()
        plt.title('Donchian Strategy')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.show()

    # Логика сделок
    df['long_exit'] = 0
    df['short_exit'] = 0
    df['profit_loss'] = 0.0

    position = None  # Текущая позиция: 'long', 'short' или None
    entry_price = 0

    for i in range(len(df)):
        # Проверяем входы
        if position is None:
            if df.loc[i, 'long_entry']:
                position = 'long'
                entry_price = df.loc[i, 'close']
            elif df.loc[i, 'short_entry']:
                position = 'short'
                entry_price = df.loc[i, 'close']

        # Проверяем выходы для лонга
        elif position == 'long':
            take_profit = entry_price * (1 + profit)
            stop_loss = entry_price * (1 - loss)

            if df.loc[i, 'close'] >= take_profit or df.loc[i, 'close'] <= stop_loss:
                df.loc[i, 'long_exit'] = 1
                df.loc[i, 'profit_loss'] = df.loc[i, 'close'] - entry_price
                position = None

        # Проверяем выходы для шорта
        elif position == 'short':
            take_profit = entry_price * (1 - profit)
            stop_loss = entry_price * (1 + loss)

            if df.loc[i, 'close'] <= take_profit or df.loc[i, 'close'] >= stop_loss:
                df.loc[i, 'short_exit'] = 1
                df.loc[i, 'profit_loss'] = entry_price - df.loc[i, 'close']
                position = None

    # Итоговая метрика стратегии
    total_trades = df['long_exit'].sum() + df['short_exit'].sum()
    total_profit = df['profit_loss'].sum()
    win_rate = (df['profit_loss'] > 0).sum() / total_trades if total_trades > 0 else 0

    print(f"Total Trades: {total_trades}")
    print(f"Total Profit: {total_profit:.2f}")
    print(f"Win Rate: {win_rate:.2%}")

    return df, total_trades, total_profit, win_rate


if __name__ == '__main__':
    data = pd.read_csv('NGF2.csv')

    list_file = [x for x in os.listdir() if x.endswith('.csv')]

    for file in list_file:
        data = pd.read_csv(file)
        profit_list = []
        win__rate_list = []
        trade_list = []
        for n in range(5, 40):
            df, total_trades, profit, win_rate = realization_strategy_donchian(data, n, 200, 0.05, 0.01)
            profit_list.append(profit)
            win__rate_list.append(win_rate)
            trade_list.append(total_trades)
        fig, ax = plt.subplots()
        ax1 = ax.twinx()
        # ax2 = ax.twinx()
        ax.plot(range(5, 40), profit_list)
        ax1.plot(range(5, 40), win__rate_list, color='red')
        # ax2.plot(range(5, 40), trade_list, color='blue')
        plt.xlabel('Donchian Period')
        plt.ylabel('Total profit')
        plt.title(f'Donchian Strategy Win Rate - {file.replace('.csv', '')}')
        plt.show()

