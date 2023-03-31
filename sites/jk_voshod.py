from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from MessagePack.message import err_log, print_exception_msg
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Восход'
SITE_URL = 'https://xn--b1aeeqvau6a.xn--p1ai/kvartirogramma#/complex'
SPREADSHEET_ID = '1_hV1K5QT04MbI9sSdBby_NA8k8LOWh8TWGRPEGYHWOo'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1LdbTYrEaI8irgVcLncJzXo9Oe6aCOlZ2YHQ-4ox8jT0'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Площадь', 'Комнат', 'Цена']

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
                    (By.CSS_SELECTOR,
                     '#nota-vito-flats > div.widget-body > div > div.widget-main__navigation > div > '
                     'div.widget-navigation__item:nth-child(4)'), 20)
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR,
                     '#nota-vito-flats > div.widget-body > div > div.widget-main__navigation > div > '
                     'div.widget-navigation__item:nth-child(4)'))
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
    list_bt = driver.get_element(
        (By.CSS_SELECTOR,
         '#nota-vito-flats > div.widget-body > div > div.widget-main__navigation > div > '
         'div.widget-navigation__item:nth-child(4)'))
    list_bt.click()
    sleep(3)
    try:
        select = driver.driver.find_element(
            By.CSS_SELECTOR,
            '#nota-vito-flats > div.widget-top > div > div.top-panel-filter.top-panel-bar__filter > select:nth-child(1)')
        options = select.find_elements(By.CSS_SELECTOR, 'option')
    except Exception as e:
        err_log(SITE_NAME + ' pars_data [select, options]', str(e))
        return None
    nan = 0
    for opt in options:
        if not app.run:
            return None
        value = opt.get_attribute('value')
        print(value)
        if value != '0':
            Select(select).select_by_value(value)
            sleep(3)
            els = driver.get_elements(
                (By.CSS_SELECTOR,
                 '#nota-vito-flats > div.widget-body > div > div.widget-main__content > div > table > tbody > tr'))
            count = len(els)
            parser.info_msg(f"квартиры: {count}")
            for el in els:
                if not app.run:
                    return None
                house_, floor_, flat_, area_, rooms_, price_ = opt.text.strip(), '', '', '', '', ''
                try:
                    floor_ = el.find_element(By.CSS_SELECTOR, "td:nth-child(7)").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [floor_]', str(e))

                try:
                    flat_ = el.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
                    if 'NaN' in flat_:
                        nan += 1
                        flat_ += f'({nan})'
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [flat_]', str(e))

                try:
                    area_ = el.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [area_]', str(e))

                try:
                    rooms_ = el.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [rooms_]', str(e))

                try:
                    price_ = el.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [price_]', str(e))

                row = [house_, floor_, flat_, area_, rooms_, price_]
                parser.add_row_info(row)

    return data
