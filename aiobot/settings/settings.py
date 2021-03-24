import pathlib

from settings.utils import get_config


BASE_DIR = pathlib.Path(__file__).parent
APP_DIR = BASE_DIR.parent

config_path = BASE_DIR / 'config' / 'main.yaml'
secret_path = BASE_DIR / 'config' / 'secret.yaml'
schedule_path = BASE_DIR / 'config' / 'schedule.yaml'

config = get_config(config_path)
secret = get_config(secret_path)
schedule = get_config(schedule_path)

LOGS_DIR = config['logs_dir']
DRIVER_FIREFOX_PATH = config['driver_firefox']
API_TOKEN = secret['telegram']['token']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config['common']['debug']

TIME_ZONE = 'Europe/Moscow'
