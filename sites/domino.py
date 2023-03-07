from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from MessagePack.message import err_log, print_exception_msg
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК "Домино'
SITE_URL = 'https://xn----htbekhoifd.xn--p1ai/#/macrocatalog/houses/3305230/bigGrid?studio=null&floorNum=1&category' \
           '=flat&activity=sell&presMode=complex '
SPREADSHEET_ID = '1sUPVMLfCt5QuOzYa0tqS0e8gdYECU7Vs3UXH2dI5UGk'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1XJVNmvn_c9k1kvQsU0rSCwrJc-C4Y5jwnof0oYm3hyQ'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Подъезд', 'Этаж', 'Квартира', 'Комнат', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS, rem_warning=True)
            # self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((By.CSS_SELECTOR, 'div.window > div > svg > path'))
            #     if not els or len(els) == 0:
            #         sleep(uniform(1, 5))
            #         self.driver.close()
            #         self.driver = WebDriver(headless=HEADLESS)
            #         self.driver.get_page(SITE_URL)
            #     else:
            #         break
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
    driver.get_page(SITE_URL)
    sleep(5)

    entrances = driver.get_elements((By.CSS_SELECTOR, 'div.chess-floors-wrap'))
    print('entrances:', len(entrances))
    for i, ent in enumerate(entrances):
        print('entrance:', i + 1)
        floors = ent.find_elements(By.CSS_SELECTOR, 'div.chess-floor')
        for j, floor in enumerate(reversed(floors)):
            print('floor:', j + 1)
            flats = floor.find_elements(By.CSS_SELECTOR, 'div.chess-item > div')
            for flat in flats:
                if not app.run:
                    return None
                color = flat.value_of_css_property('background-color')
                if color == 'rgba(167, 239, 170, 1)':
                    entrance_, floor_, flat_, type_, area_, price_ = i + 1, j + 1, '', '', '', ''
                    # Квартира
                    try:
                        flat_ = flat.find_element(
                            By.XPATH, './div/div[1]').text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                    # Комнат
                    try:
                        type_ = flat.find_element(
                            By.XPATH, './div/div[2]').text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [type_]', str(e))
                    # Площадь
                    try:
                        area_ = flat.find_element(
                            By.XPATH, './div[3]/span[1]').text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [area_]', str(e))
                    # Цена
                    try:
                        price_ = flat.find_element(
                            By.XPATH, './div[2]').text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [price_]', str(e))

                    row = [entrance_, floor_, flat_, type_, area_, price_]
                    parser.add_row_info(row)

    return data

