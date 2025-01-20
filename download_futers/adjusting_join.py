import os
import pandas as pd

# Список файлов с фьючерсами
list_file = [x for x in os.listdir() if 'NG' in x]

def get_expiry_date(file):
    """
    Получить дату экспирации из файла.
    """
    data = pd.read_csv(file)
    data['time'] = pd.to_datetime(data['time'])
    return data['time'].max()

# Сортируем файлы по дате экспирации
list_file.sort(key=get_expiry_date)

# Читаем данные и объединяем с коррекцией
full_data = pd.DataFrame()
price_adjustment = 0  # Коррекция цены между контрактами

for i, file in enumerate(list_file):
    data = pd.read_csv(file)
    data['time'] = pd.to_datetime(data['time'])

    if i == 0:
        full_data = data
    else:
        # Последняя цена предыдущего контракта
        last_date = full_data['time'].max()
        last_price = full_data.loc[full_data['time'] == last_date, 'close'].iloc[0]

        # Первая цена текущего контракта
        try:
            first_price = data[data['time'] > last_date]['close'].iloc[0]
        except:
            break

        # Рассчитываем разницу для коррекции
        price_adjustment = last_price - first_price
        print(price_adjustment)

        # Корректируем цены текущего контракта
        data['close'] += price_adjustment
        data['high'] += price_adjustment
        data['low'] += price_adjustment
        data['open'] += price_adjustment

        # Берём только строки, которые идут после последней даты предыдущего контракта
        data = data[data['time'] > last_date]
        full_data = pd.concat([full_data, data])

# Сортируем итоговые данные по времени
full_data.sort_values('time', inplace=True)

# Сохраняем итоговые данные
full_data.to_csv('gas_back_adjusted.csv', index=False)
