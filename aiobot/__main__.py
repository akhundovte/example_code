import os
import jinja2

from db import db_engine
from utils.jinja2 import jinja_render, get_filters
from settings.settings import schedule, APP_DIR, config
from settings.log import configure_logging
from utils.scheduler import Scheduler


def start_bot():
    from apps.shopwatcher.bot import dp
    from aiogram import executor
    from routes import setup_routes

    scheduler = Scheduler(schedule)
    scheduler.start()

    setup_routes(dp)
    executor.start_polling(dp,
                           on_shutdown=on_shutdown,
                           on_startup=on_startup,
                           skip_updates=True
                           )


async def on_startup(dispatcher):
    await db_engine.create(config['postgres_db'])

    path = os.path.join(APP_DIR, 'apps/shopwatcher/templates')
    jinja_render.setup(
        loader=jinja2.FileSystemLoader(path),
        filters=get_filters(),
        trim_blocks=True,
        lstrip_blocks=True,
        )


async def on_shutdown(dispatcher):
    await db_engine.close()


if __name__ == '__main__':
    configure_logging()
    start_bot()
