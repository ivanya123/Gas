import pandas as pd

import matplotlib.pyplot as plt


data = pd.read_csv('DATA_GAZ.csv')

fig, ax = plt.subplots()
ax.plot(pd.to_datetime(data['time']), data['close'])
plt.show()