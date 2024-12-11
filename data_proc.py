import pandas as pd
import matplotlib.pyplot as plt


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


# Пример использования
df_with_lags = pd.read_csv('candles.csv')
df_with_lags['time'] = pd.to_datetime(df_with_lags['time'])
df_with_lags = df_with_lags.sort_values('time').reset_index(drop=True)

# Допустим, у нас есть столбцы ['open', 'high', 'low', 'close', 'volume']
feature_columns = ['open', 'high', 'low', 'close', 'volume']

df_with_lags = create_lag_features(df_with_lags, feature_columns, forward_lags=5, backward_lags=5)
print(df_with_lags[df_with_lags['signal'] == 1])

fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(df_with_lags['time'], df_with_lags['close'], label='Close Price', color='blue')

# Фильтруем строки, где есть сигнал
entry_points = df_with_lags[df_with_lags['signal'] == 1]

# Добавляем вертикальные линии в точках входа
# Можно использовать ax.axvline, если хотим рисовать для каждой точки
for _, row in entry_points.iterrows():
    ax.axvline(x=row['time'], color='red', linestyle='--', alpha=0.7)

# Дополнительные настройки:
ax.set_title('Close Price with Entry Points')
ax.set_xlabel('Time')
ax.set_ylabel('Price')
ax.legend()

plt.tight_layout()
plt.show()