from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Лето'
SITE_URL = 'https://leto.masterstroydv.ru/planning/'
SPREADSHEET_ID = '1k8FemOqSOSW71jYVCD-wp8PvZvLhOP4tSHDZRSTH1QE'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1RRRQevlVRIKwFSdJL1y5R8bG9oPzMms2u3aOmr_j4qM'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', 'Квартира', 'Тип', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS)
            self.driver.get_page(SITE_URL)
            for i in range(5):
                els = self.driver.get_elements((By.CSS_SELECTOR, 'body > div.Layout > main > section > div > section > '
                                                                 'div > div > div > svg > a'))
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
    for i in range(969, 986, 1):
        if not app.run:
            return None
        url = f'https://leto.masterstroydv.ru/planning/5/{i}/'
        driver.get_page(url)
        sleep(1)
        els = driver.get_elements((By.CSS_SELECTOR, 'svg.Floor__svg > a > polygon.Floor__polygon.Floor__polygon'
                                                    '--available'))
        parser.info_msg(f'Квартир: {len(els)}')
        for el in els:
            row, flat_ = get_row_data(driver, el, 5)
            parser.add_row_info(row, 5, flat_)

    for i in range(987, 1004, 1):
        if not app.run:
            return None
        url = f'https://leto.masterstroydv.ru/planning/6/{i}/'
        driver.get_page(url)
        sleep(1)
        els = driver.get_elements((By.CSS_SELECTOR, 'svg.Floor__svg > a > polygon.Floor__polygon.Floor__polygon'
                                                    '--available'))
        parser.info_msg(f'Квартир: {len(els)}')
        for el in els:
            row, flat_ = get_row_data(driver, el, 6)
            parser.add_row_info(row, 6, flat_)

    return data


def get_row_data(driver, el, h):
    house_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
    try:
        house_ = h
        text = el.get_attribute('data-bs-original-title')
        flat_ = int(text.split('<h3>')[1].split('</h3>')[0].strip())
        type_ = text.split('<h4>')[1].split('</h4>')[0].strip()
        area_ = text.split('Площадь:')[1].split('</p>')[0].strip()
        price_ = text.split('Цена:')[1].split('</p>')[0].strip()
        floor_ = driver.get_element((By.CSS_SELECTOR, 'body > div.Layout > main > section > div > main > '
                                                      'section.Floor__levelsWrapper > div > div > div > ul >'
                                                      ' li > a.Floor__level.Floor__level--active'))
        floor_ = int(floor_.text.strip())
    except Exception as e:
        err_log(SITE_NAME + ' get_flat_info [pars_data]', str(e))
    row = [house_, floor_, flat_, type_, area_, price_]
    return row, flat_
