from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from MessagePack.message import err_log, print_exception_msg
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Мед'
SITE_URL = 'https://xn----gtbbb8aen.xn--p1ai/apartment/'
SPREADSHEET_ID = '1cNopzY1k5DciOtoKgQMjrLVo49pHq_YRiFUFt1WlOVs'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1rNl6KtqfOnaD8LjPSgHghPJMKqT0tb5Y10_VEOwRSYE'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Этаж', '№ квартиры', 'Площадь', 'Цена']

data = []


class SiteParser(QThread):
    def __init__(self, app, name, stream):
        super().__init__()
        self.app = app
        self.name = name
        self.stream = stream
        self.time = time()

    def add_row_info(self, row, index_1=None, index_2=None):
        check = np.array(row)
        empty = True
        for cell in row:
            if cell != '':
                empty = False
                break
        if len(row) == 0 or empty:
            return
        for r in data:
            if np.array_equal(check, np.array(r)):
                return
        index_1 = '' if index_1 is None else Fore.BLUE + f'[{index_1}]'
        index_2 = '' if index_2 is None else Fore.BLUE + f'[{index_2}]'
        print(Fore.YELLOW + f'[PARSER {self.stream}]', index_1, index_2, Style.RESET_ALL + f'{row}')
        data.append(row)

    def info_msg(self, msg):
        print(Fore.YELLOW + f'[PARSER {self.stream}]', Style.RESET_ALL + str(msg))

    def delete(self):
        if self.driver:
            print('del driver for', self.name)
            self.driver.close()

    def _create_driver(self):
        try:
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=False)
            self.driver.get_page(SITE_URL, )
            for i in range(5):
                sleep(3)
                self.driver.waiting_for_element(
                    (By.CSS_SELECTOR, '#flat > button'), 20)
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR, '#flat > button'))
                if not els or len(els) == 0:
                    sleep(uniform(1, 5))
                    self.driver.close()
                    self.driver = WebDriver(headless=HEADLESS)
                    self.driver.get_page(SITE_URL)
                else:
                    break
        except Exception as e:
            err_log(SITE_NAME + '_create_driver', str(e))

    def run(self):
        self.info_msg(f'start parser: {self.name}')
        self._create_driver()
        data_ = pars_data(self)
        count = 0 if data_ is None else len(data_)
        if data_ and len(data_) > 0:
            gspread_update(data_, HEADER, SPREADSHEET_ID, SHEET_ID)  # gspread update_sheet_data()
        self.app.parser_result(self.name, count, time() - self.time)
        self.app.next_parser(self.name, self.stream)
        try:
            self.driver.close()
        except Exception as e:
            err_log(SITE_NAME + '[SiteParser] run', str(e))
        self.quit()


@timer_func
@try_func
def pars_data(parser):
    data.clear()
    app = parser.app
    driver = parser.driver
    driver.driver.maximize_window()
    sleep(1)
    while True:
        more_bts = driver.get_elements((By.CSS_SELECTOR, '#flat > button'))
        if len(more_bts) > 0 and "choose-params__load--hide" not in more_bts[0].get_attribute('class'):
            try:
                more_bts[0].click()
            except Exception as e:
                pass
            sleep(2)
        else:
            break
    sleep(1)

    els = driver.get_elements((By.CSS_SELECTOR, '#flat > div.flat-cards > div'))
    parser.info_msg(f"квартиры: {len(els)}")
    for el in els:
        if not app.run:
            return None
        floor_, flat_, area_, price_ = '', '', '', ''
        try:
            floor_ = el.find_element(
                By.CSS_SELECTOR,
                'div.flat-card__main > div.flat-card__info > div.flat-card__params > div:nth-child(2) > '
                'span:nth-child(2) > span').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [floor_]', str(e))

        try:
            flat_ = el.find_element(
                By.CSS_SELECTOR,
                'div.flat-card__main > div.flat-card__info > div.flat-card__title').text.split('№')[1].strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [flat_]', str(e))

        try:
            area_ = el.find_element(
                By.CSS_SELECTOR,
                'div.flat-card__main > div.flat-card__info > div.flat-card__params > div:nth-child(3) > '
                'span:nth-child(2) > span').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [area_]', str(e))

        try:
            price_ = el.find_element(
                By.CSS_SELECTOR,
                'div.flat-card__main > div.flat-card__price').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [price_]', str(e))

        row = [floor_, flat_, area_, price_]
        parser.add_row_info(row)

    return data
