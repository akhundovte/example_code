
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from settings import settings


# Initialize bot and dispatcher
bot = Bot(token=settings.API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
