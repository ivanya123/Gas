import pandas as pd

df = pd.read_csv('daily_futures.csv', decimal=',')
df['Дата'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y')
print(df)
