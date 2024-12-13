import matplotlib.pyplot as plt
import pandas as pd

from data_proc import create_signal_reversal


def small_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    entry_point = df[df['signal_reversal'] == 1].index
    for i in entry_point:
        yield df.iloc[i - 10:i + 10, :]


df = pd.read_csv('candles.csv')
df['time'] = pd.to_datetime(df['time'], format='%Y-%m-%d %H:%M:%S+00:00')
df = df.sort_values(by='time').reset_index(drop=True)
df = create_signal_reversal(df, threshold=0.002)

for small_df in small_dataframe(df):
    fig, ax = plt.subplots()
    ax.plot(small_df['time'], small_df['close'])
    ax.plot(small_df['time'], small_df['sma'])
    entry = small_df[small_df['signal_reversal'] == 1]
    ax.scatter(entry['time'], entry['close'])
    ax.grid()
    plt.show()
# print(df[df['signal_reversal'] == 1])


# fig, ax = plt.subplots()
# ax.plot(df['time'], df['close'])
# ax.plot(df['time'], df['sma'])
#
# entry = df[df['signal_reversal'] == 1]
#
# ax.scatter(entry['time'], entry['close'])
#
# plt.show()
