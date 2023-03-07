from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Суприм дом'
SITE_URL = 'https://xn----htbkqclcihu.xn--p1ai/podbor-po-parametram?tfc_storepartuid[540347509]=Этаж+4&tfc_div=:::'
SPREADSHEET_ID = '1E2QfKwZEoJW3lIdE_LGXrw_WOpl4hm9UFsxnxCD2fjY'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1UtT22GjTzy9SMt-PkxU3llLlph3V2MyzNB8ygSR1g9A'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Площадь', 'Комнат', 'Цена']
HOUSES = [(4, 26), (4, 26), (4, 15)]

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
                sleep(3)
                self.driver.waiting_for_element(
                    (By.XPATH,
                     '//*[@id="rec540347509"]/div[1]/div/div[1]/div/div[3]/div/a/div[2]'), 20)
                els = self.driver.get_elements((
                    By.XPATH,
                    '//*[@id="rec540347509"]/div[1]/div/div[1]/div/div[3]/div/a/div[2]'
                ))
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
    driver_1 = WebDriver(headless=HEADLESS)

    all_floors, all_flats = 0, 0
    for i, range_ in enumerate(HOUSES):
        house_ = i + 1
        for j in range(*range_):
            floor_ = j
            if not app.run:
                return None
            driver.get_page(
                f"https://xn----htbkqclcihu.xn--p1ai/podbor-po-parametram?tfc_storepartuid[540347509]=Этаж+{floor_}&tfc_div=:::")
            driver.waiting_for_element(
                (By.XPATH,
                 '//*[@id="rec540347509"]/div[1]/div/div[1]/div/div[3]/div/a/div[2]'), 20)
            sleep(1)
            els = driver.get_elements((
                By.XPATH,
                '//*[@id="rec540347509"]/div[1]/div/div[1]/div/div[3]/div/a'
            ))
            parser.info_msg(f"комплекс: {house_}, этаж: {floor_}, квартиры: {len(els)}")
            all_floors += 1
            all_flats += len(els)

            for el in els:
                if not app.run:
                    return None

                flat_, area_, price_ = el.text.strip().split('\n')
                rooms_ = ''
                try:
                    href = el.get_attribute('href')
                    driver_1.get_page(href)
                    sleep(1)
                    rooms_ = driver_1.get_element(
                        (By.XPATH,
                         '//*[@id="rec540347509"]/div[1]/div[2]/div/div/div[2]/div[7]/div[2]/p[2]'))
                    rooms_ = rooms_.text.split('Количество комнат:')[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [rooms_]', str(e))
                row = [house_, floor_, flat_, area_, rooms_, price_]
                parser.add_row_info(row)
                # break
    print('всего этажей:', all_floors)
    print('всего квартир:', all_flats)
    return data
