import pandas as pd

import matplotlib.pyplot as plt


data = pd.read_csv('DATA_GAZ.csv')
data_2 = pd.read_csv('gas_back_adjusted.csv')

fig, ax = plt.subplots()
ax.plot(pd.to_datetime(data['time']), data['close'])
ax.plot(pd.to_datetime(data_2['time']), data_2['close'])
plt.show()