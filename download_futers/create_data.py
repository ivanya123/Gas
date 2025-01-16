from enum import Enum

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
                                  length_short_sma: int = 30,
                                  length_long_sma: int = 200,
                                  short_donchian_parameters: int = 20,
                                  long_donchian_parameters: int = 200,
                                  evaluation_parameter: EvalParameter = EvalParameter.CLOSE.value,
                                  period_mean_price_target: int = 10,
                                  period_max_price_target: int = 5) -> tuple[pd.DataFrame, list[str], list[str]]:
    '''
    Функция для создания датафрейма для обучения модели.
    :param df: Датафрейм с данными часовых свеч по фьючерсу
    :param length_short_sma: Длина короткой скользящей средней
    :param length_long_sma: Длина длинной скользящей средней
    :param short_donchian_parameters: Параметр показывающей период короткого канала Дончяна
    :param long_donchian_parameters: Параметр показывающей период длинного канала Дончяна
    :param evaluation_parameter: По какому столбцу считать параметры.
    :return: Датафрейм с данными для обучения модели, список столбцов парметров, список столбцов целевого признака
    '''
    l_columns: list[str] = [f'sma_close_{length_short_sma}',
                            f'sma_close_{length_long_sma}',
                            f'max_donchian_close_{short_donchian_parameters}',
                            f'min_donchian_close_{short_donchian_parameters}',
                            f'max_donchian_close_{long_donchian_parameters}',
                            f'min_donchian_close_{long_donchian_parameters}',
                            f'mean_donchian_close_{short_donchian_parameters}',
                            f'mean_donchian_close_{long_donchian_parameters}',
                            'close',
                            'high',
                            'low',
                            'volume',
                            'time']
    df['time'] = pd.to_datetime(df['time'])
    df[f'sma_close_{length_short_sma}'] = df[f'{evaluation_parameter}'].rolling(length_short_sma).mean()
    df[f'sma_close_{length_long_sma}'] = df[f'{evaluation_parameter}'].rolling(length_long_sma).mean()
    df[f'max_donchian_close_{short_donchian_parameters}'] = (
        df[f'{evaluation_parameter}'].rolling(short_donchian_parameters).max()
    )

    df[f'min_donchian_close_{short_donchian_parameters}'] = (
        df[f'{evaluation_parameter}'].rolling(short_donchian_parameters).min()
    )

    df[f'max_donchian_close_{long_donchian_parameters}'] = (
        df[f'{evaluation_parameter}'].rolling(long_donchian_parameters).max()
    )

    df[f'min_donchian_close_{long_donchian_parameters}'] = (
        df[f'{evaluation_parameter}'].rolling(long_donchian_parameters).min()
    )

    df[f'mean_donchian_close_{short_donchian_parameters}'] = (df[f'max_donchian_close_{short_donchian_parameters}'] -
                                                              df[f'min_donchian_close_{short_donchian_parameters}']) / 2

    df[f'mean_donchian_close_{long_donchian_parameters}'] = (df[f'max_donchian_close_{long_donchian_parameters}'] -
                                                             df[f'min_donchian_close_{long_donchian_parameters}']) / 2

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





if __name__ == '__main__':
    data = pd.read_csv('NGF2.csv')
    new_data, l_col, target_columns = create_dataframe_for_learning(data)
    # new_data.to_csv('NGF2_full_dataframe.csv')
    print(l_col)
