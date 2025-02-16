import asyncio
from bot.telegram_bot import bot, dp, scheduler
from bot.handlers import start_router, connect
from config import CHAT_ID
from trad.task_all_time import update_data, start_bot, processing_stream, conclusion_in_day, processing_stream_portfolio


async def main():
    dp.include_router(start_router)
    scheduler.start()
    kwargs = {
        'connect': connect,
        'bot': bot
    }
    scheduler.add_job(update_data, 'cron', kwargs=kwargs, hour=8, minute=50)
    scheduler.add_job(conclusion_in_day, 'cron', kwargs=kwargs, hour='14,21', minute=0)
    await start_bot(connect=connect, bot=bot)
    task_stream_msg = asyncio.create_task(processing_stream(connect=connect, bot=bot))
    task_stream_portfolio = asyncio.create_task(processing_stream_portfolio(connect=connect, bot=bot))
    await bot.send_message(chat_id=CHAT_ID, text='Бот запустился')
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())
