from random import uniform, choice
from time import sleep, time

import numpy as np
from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium.webdriver.common.by import By

from MessagePack import print_exception_msg, print_info_msg
from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_spreadsheets import add_spreadsheet_data, get_service, replace_sheet, add_data_to_sheet_by_name
from g_gspread import update_sheet_data as gspread_update

HEADLESS = True
SITE_NAME = 'brusnika-dom.ru'
SITE_URL = 'https://brusnika-dom.ru/выбор-квартир-таблица/'
SPREADSHEET_ID = '1XdBVvfpHLlYkXLfpHYsrCYm4hahMX_-no0oANpHacao'  # заказчика
SHEET_ID = 1  # заказчика
SHEET_NAME = 'Лист2'  # заказчика
# SPREADSHEET_ID = '1gx_dCPMI_2ygTqxcnMMY_MGnSEjcDerwaFOqPTYlbgI'  # мой
# SHEET_ID = 1  # мой
# SHEET_NAME = 'Лист2'  # мой
HEADER = ['Квартира', 'Цена', 'Этаж', 'Подъезд', 'Площадь', 'Статус', 'Дом']

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
                els = self.driver.get_elements((By.CSS_SELECTOR, '#wpt_table > tbody > tr'))
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
    els = driver.get_elements((By.CSS_SELECTOR, '#wpt_table > tbody > tr'))
    while els:
        if not app.run:
            return None
        try:
            els = driver.get_elements((By.CSS_SELECTOR, '#wpt_table > tbody > tr'))
            el = els[-1].find_element(By.CSS_SELECTOR, 'td:nth-child(2) a').text
            if 'Квартира' not in el:
                break
            bt = driver.get_element((By.CSS_SELECTOR, '#wpt_load_more_wrapper_1800 > button'))
            bt.click()
            sleep(3)
        except Exception as e:
            print_exception_msg(str(e))
    parser.info_msg(f'els: {len(els)}')
    for el in els:
        if not app.run:
            return None
        flat_, price_, floor_, entrance_, area_, status_, house_ = '', '', '', '', '', '', ''
        # квартира, дом
        try:
            el_ = el.find_element(By.CSS_SELECTOR, 'td:nth-child(2) a').text
            if 'Квартира' not in el_:
                return data
            flat_ = el_.split('\n')[0]
            house_ = el_.split('\n')[1]
        except Exception as e:
            err_log(SITE_NAME + ' pars_data[квартира, дом]', str(e))
        # цена
        try:
            price_ = el.find_element(By.CSS_SELECTOR, 'td:nth-child(4) div').text
        except Exception as e:
            err_log(SITE_NAME + ' pars_data[цена]', str(e))
        # этаж
        try:
            floor_ = el.find_element(By.CSS_SELECTOR, 'td:nth-child(6) div div:nth-child(5)').text\
                .replace('Этаж', 'Этаж ')
        except Exception as e:
            err_log(SITE_NAME + ' pars_data[этаж]', str(e))
        # подъезд
        try:
            entrance_ = (int(flat_.split(' ')[1]) - 1) // 12 + 1
        except Exception as e:
            err_log(SITE_NAME + ' pars_data[подъезд]', str(e))
        # плошадь
        try:
            area_ = el.find_element(By.CSS_SELECTOR, 'td:nth-child(6) div div:nth-child(1)').text\
                .replace('Жилая площадь', '')
        except Exception as e:
            err_log(SITE_NAME + ' pars_data[жилая площадь]', str(e))
        # статус
        try:
            status_ = el.find_element(By.CSS_SELECTOR, 'td:nth-child(3) div p').text
        except Exception as e:
            err_log(SITE_NAME + ' pars_data[статус]', str(e))
        row = [flat_, price_, floor_, entrance_, area_, status_, house_]
        parser.add_row_info(row)
    return data

