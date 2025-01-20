import os

import pandas as pd

list_file = [x for x in os.listdir() if 'NG' in x]


def filter_futures(file: str) -> str:
    data = pd.read_csv(file)
    return data['time'].min()


list_file.sort(key=filter_futures)

list_data = [pd.read_csv(file) for file in list_file]

full_data = list_data[0]
for index, data in enumerate(list_data[1:], start=1):
    date_last = list_data[index - 1]['time'].max()
    data_next = data[data['time'] > date_last]
    full_data = pd.concat([full_data, data_next], ignore_index=True)

full_data.sort_values('time', inplace=True)
full_data = full_data.set_index('time')
full_data.to_csv('DATA_GAZ.csv')

full_data = list_data[0]
price_adjustment = 0
for index, data in enumerate(list_data[1:], start=1):
    date_last = list_data[index - 1]['time'].max()

    last_price = full_data.loc[full_data['time'] == date_last, 'close'].iloc[0]
    first_price = data.loc[data['time'] > date_last, 'close'].iloc[0]

    price_adjustment += last_price - first_price

    data['close'] = data['close'] - price_adjustment
    data['high'] = data['high'] - price_adjustment
    data['low'] = data['low'] - price_adjustment
    data['open'] = data['open'] - price_adjustment

    data_next = data[data['time'] > date_last]
    full_data = pd.concat([full_data, data_next], ignore_index=True)


# Сортируем итоговые данные по времени
full_data.sort_values('time', inplace=True)

# Сохраняем итоговые данные
full_data.to_csv('gas_back_adjusted.csv', index=False)
