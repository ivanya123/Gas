import pandas as pd
import matplotlib.pyplot as plt

from data_proc import create_signal_reversal, create_lag_features


df = pd.read_csv('candles.csv')
df['time'] = pd.to_datetime(df['time'], format='%Y-%m-%d %H:%M:%S+00:00')
df = df.sort_values(by='time').reset_index(drop=True)
df = create_signal_reversal(df.head(24), threshold=0.0015)
print(df)
# print(df[df['signal_reversal'] == 1])


fig, ax = plt.subplots()
ax.plot(df['time'], df['close'])
ax.plot(df['time'], df['sma'])

entry = df[df['signal_reversal'] == 1]

ax.scatter(entry['time'], entry['close'])

plt.show()