from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from settings.settings import DRIVER_FIREFOX_PATH


class CookieDriver:

    def __init__(self):
        options = Options()
        options.headless = True
        # в этот момент запускается процесс с браузером и драйвером
        self.driver = webdriver.Firefox(
            executable_path=DRIVER_FIREFOX_PATH,
            options=options
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_cookies(self, url, cookie_name=None):
        self.driver.get(url)
        cookies_l = self.driver.get_cookies()
        cookies = {}

        if cookie_name is None:
            for item in cookies_l:
                cookies[item['name']] = item['value']
        else:
            for item in cookies_l:
                item_name = item['name']
                if cookie_name == item_name or cookie_name in item_name:
                    cookies[item_name] = item['value']
                    break
        return cookies

    def close(self):
        """Если не выйти остается процесс браузера."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __del__(self):
        self.close()
