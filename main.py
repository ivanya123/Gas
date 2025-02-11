import asyncio
from bot.telegram_bot import bot, dp
from bot.handlers import start_router


async def main():
    dp.include_router(start_router)
    # await dp.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())