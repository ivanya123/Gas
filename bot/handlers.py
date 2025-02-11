import asyncio
from aiogram import Router, F
from aiogram.types import Message
from tinkoff.invest import MarketDataResponse
from bot.telegram_bot import bot  # Если bot импортирован глобально, можно использовать его напрямую
from trad.connect_tinkoff import ConnectTinkoff
from config import TOKEN

start_router = Router()

async def stream_cocoa(message: Message):
    connect = ConnectTinkoff(TOKEN)
    await connect.connect()  # Инициализация клиента и стриминга
    # Получаем исторические данные по инструменту CCH5 с интервалом 1h
    historic_cocoa, instrument_info = await connect.get_candles_from_ticker('CCH5', '1h')
    # Подписываемся на стрим свечей по инструменту
    await connect.add_subscribe(instrument_info.uid)
    # Цикл обработки сообщений из очереди
    try:
        while True:
            msg: MarketDataResponse = await connect.queue.get()  # убедитесь, что queue инициализирован
            if msg.candle:
                await bot.send_message(chat_id=message.chat.id, text=str(msg.candle.high))
            # Можно добавить условие для выхода, например, по команде или таймауту
    except Exception as e:
        # Логируем или обрабатываем исключение
        print(f"Ошибка в stream_cocoa: {e}")

@start_router.message(F.text == 'Cocoa')
async def start(message: Message):
    # Запускаем фоновую задачу для стриминга
    asyncio.create_task(stream_cocoa(message))
