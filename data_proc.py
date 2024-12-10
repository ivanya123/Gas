import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('candles.csv')
df['time'] = pd.to_datetime(df['time'])


plot = df.plot(x='time', y='close')

def create_signal(data: pd.DataFrame) -> pd.DataFrame:
    pass
