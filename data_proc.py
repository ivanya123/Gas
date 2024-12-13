import numpy as np
import pandas as pd


def create_lag_features(data: pd.DataFrame, columns: list, forward_lags: int = 5,
                        backward_lags: int = 5) -> pd.DataFrame:
    # Предполагается, что data уже отсортирован по времени
    # columns - список признаков, для которых мы хотим сделать сдвиги
    # forward_lags - число временных шагов для сдвига вперёд
    # backward_lags - число временных шагов для сдвига назад

    # Создадим копию, чтобы не изменять оригинал
    df = data.copy()

    # Создание сдвигов назад (положительные сдвиги)
    for i in range(1, forward_lags + 1):
        shifted = df[columns].shift(i)
        shifted.columns = [f"{col}_{i}" for col in shifted.columns]
        df = pd.concat([df, shifted], axis=1)

    # Создание сдвигов вперёд (отрицательные сдвиги)
    for i in range(1, backward_lags + 1):
        shifted = df[columns].shift(-i)
        shifted.columns = [f"{col}_{-i}" for col in shifted.columns]
        df = pd.concat([df, shifted], axis=1)

    df = df.dropna()

    mask = (df['close_3'] > df['close_2']) & \
           (df['close_2'] > df['close_1']) & \
           (df['close_1'] > df['close']) & \
           (df['close'] > df['close_-1']) & \
           (df['close_-1'] > df['close_-2'])

    df['signal'] = 0
    df.loc[mask, 'signal'] = 1

    return df


def create_signal_reversal(data: pd.DataFrame, window: int = 5, threshold: float = 0.01):
    """
    Создаёт целевое значение для предсказания момента изменения тренда.
    1 означает, что на этой свече произошла смена направления тренда.
    0 - иначе.

    Параметры:
    - df: DataFrame с колонкой 'close'
    - window: размер окна для сглаживания (скользящее среднее)
    - threshold: порог для отсечения шума (например, 0.5%)
      Если изменение тренда происходит без существенного изменения цены,
      считаем, что это шум и не ставим сигнал.

    Предполагается, что df отсортирован по времени.
    """
    df = data.copy()
    df = df.sort_values('time').reset_index(drop=True)
    df['sma'] = df['close'].rolling(window, center=True, min_periods=1).mean()
    df['diff'] = df['sma'].diff()
    df['diff_abs_pct'] = df['diff'].abs() / df['sma']
    df['trend_dir'] = np.sign(df['diff'])
    # В разворотах signal_reversal=1, когда trend_dir меняется и изменение цены выше threshold
    # Например:
    df['signal_reversal'] = 0
    for i in range(1, len(df)):
        if df.loc[i - 1, 'trend_dir'] != 0 and df.loc[i, 'trend_dir'] != 0:
            if df.loc[i - 1, 'trend_dir'] != df.loc[i, 'trend_dir']:
                # Проверяем величину изменения
                if df.loc[i, 'diff_abs_pct'] > threshold:
                    df.loc[i, 'signal_reversal'] = 1
    return df
