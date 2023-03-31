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
SITE_NAME = 'ЖК Инлав'
SITE_URL = 'https://xn--80aaau8ahjjse3h.xn----7sbgjqslco.xn--p1ai/?tab=1'
SPREADSHEET_ID = '1iEiCXXMn9SLhKSxaRNWKEq1ZhxIAVc3mrMs1gE0UXfY'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1TTNPJLSwFFI7Mc4e4E9pMyTb3BJqpi0m3KjU0ONb5-s'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Этаж', '№ квартиры', 'Площадь', 'Комнат', 'Цена']

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
                    (By.CSS_SELECTOR, 'a.apartmentCard'), 20)
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR, 'a.apartmentCard'))
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
    sleep(3)
    els, count = [], 0
    while True:
        els = driver.get_elements((By.CSS_SELECTOR, 'a.apartmentCard'))
        count_ = len(els)
        if count_ > count:
            count = count_
            driver.driver.execute_script("arguments[0].scrollIntoView();", els[count_ - 1])
            sleep(1)
        else:
            break
    parser.info_msg(f"квартиры: {count}")
    for el in els:
        if not app.run:
            return None
        floor_, flat_, area_, rooms_, price_ = '', '', '', '', ''
        try:
            floor_ = el.find_element(
                By.CSS_SELECTOR,
                "div.apartmentCard__wrapper > div:nth-child(1) > div.apartmentCard__info-value").text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [floor_]', str(e))

        try:
            text = el.find_element(
                By.CSS_SELECTOR,
                "div > div:nth-child(2) > div.apartmentCard__title").text
            flat_ = text.split('№')[1].strip()
            rooms_ = text.split('№')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [flat_, rooms_]', str(e))

        try:
            area_ = el.find_element(
                By.CSS_SELECTOR,
                "div.apartmentCard__wrapper > div:nth-child(2) > div.apartmentCard__info-value").text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [area_]', str(e))

        try:
            price_ = el.find_element(By.CSS_SELECTOR, "div.apartmentCard__price").text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [price_]', str(e))

        row = [floor_, flat_, area_, rooms_, price_]
        parser.add_row_info(row)

    return data
