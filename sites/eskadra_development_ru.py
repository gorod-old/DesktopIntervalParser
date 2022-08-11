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
import numpy as np

HEADLESS = True
SITE_NAME = 'eskadra-development.ru'
SITE_URL = 'https://eskadra-development.ru/live-property/choose/?f[perpage]=all&f[sort]=&f[sort_dst]=&f[price1]=0&f[' \
           'price2]=11+778+679&f[sq1]=26&f[sq2]=157&f[floor1]=1&f[floor2]=23&f[smart_type]=1 '
SPREADSHEET_ID = '128PrfeWxOpEvYmZ1imHkK6KOOTvfm3ggjbpxDduxs8s'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1l69nz3ZnKccITNfC2dOQkr9uhUPZETBvIFPjNQHMyyo'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Объект', 'Квартира', 'Этаж', 'Площадь', 'Цена', 'Статус']

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
                els = self.driver.get_elements((By.CSS_SELECTOR, '#flats_cont > div.flats.cleaner > div.item > a'))
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
        if data_ and len(data_) > 0:
            gspread_update(data_, HEADER, SPREADSHEET_ID, SHEET_ID)  # gspread update_sheet_data()
        self.app.parser_result(self.name, len(data), time() - self.time)
        self.app.next_parser(self.name)
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
    els = driver.get_elements((By.CSS_SELECTOR, '#flats_cont > div.flats.cleaner > div.item'))
    parser.info_msg(f'Квартиры: {len(els)}')
    for el in els:
        if not app.run:
            return None
        row = []
        obj, flat, floor, square, price, status = '', '', '', '', '', ''
        if 'цена:' in el.text.lower():
            try:
                text = el.text
                flat = text.split('№')[0] + ' №' + text.split('№')[1].split('\n')[0]
            except Exception as e:
                err_log('pars_data [Квартира]', str(e))
            try:
                text = el.find_element(By.CSS_SELECTOR, 'span').text
                obj = text.split('Площадь:')[0].strip()
                square = text.split('Площадь:')[1].split('Этаж:')[0].strip()
                floor = text.split('Этаж:')[1].split('Цена:')[0].strip()
                price = text.split('Цена:')[1].strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [Объект, площадь, этаж, цена]', str(e))
            try:
                status = el.find_element(By.CSS_SELECTOR, 'div.booked')
                if status:
                    status = 'забронировано'
            except Exception as e:
                pass
            row.extend([obj, flat, floor, square, price, status])
            parser.add_row_info(row)
    return data

