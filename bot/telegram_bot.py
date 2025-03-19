import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
load_dotenv()
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN_TELEGRAM = os.getenv('TOKEN_TELEGRAM')
print(TOKEN_TELEGRAM)
scheduler = AsyncIOScheduler(timezone='Europe/Moscow')

FORMAT = '[%(asctime)s:%(name)s-%(funcName)s-%(lineno)d:%(levelname)s] - %(message)s'
formatter = logging.Formatter(FORMAT)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

file_handler = RotatingFileHandler('logs/logs.log', mode='a', maxBytes=10 * 1024 * 1024, backupCount=15)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logging.basicConfig(level=logging.DEBUG, handlers=[stream_handler, file_handler])
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN_TELEGRAM, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
