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
SITE_NAME = 'ЖК Флагман'
SITE_URL = 'https://fsk.ru/flagman-vlad/flats'
# SPREADSHEET_ID = ''  # заказчика
# SHEET_ID = 0  # заказчика
# SHEET_NAME = 'Лист1'  # заказчика
SPREADSHEET_ID = '1HpIn_PHWlIlRWGG6FUwLuxiBr2zfxQ5mgajCSyFRCH4'  # мой
SHEET_ID = 0  # мой
SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'секция', 'Этаж', '№ квартиры', 'Тип', 'Площадь', 'Цена']

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
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR, '#__layout > div > main > section > div > div.flat-wrapper > a'))
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
    try:
        selector = '#__layout > div > div.accept-cookies > div > button'
        cookies_bt = driver.get_element((By.CSS_SELECTOR, selector))
        cookies_bt.click()
        sleep(3)
    except Exception as e:
        pass
    flats = []
    while True:
        selector = '#__layout > div > main > section > div > div.flat-wrapper > a'
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
        flats = driver.get_elements((By.CSS_SELECTOR, selector))
        parser.info_msg(f'Квартиры: {len(flats)}')
        try:
            selector = '#__layout > div > main > section > div > div.flat-wrapper > button'
            bt_more = driver.get_element((By.CSS_SELECTOR, selector))
            webdriver.ActionChains(driver.driver).move_to_element(bt_more).pause(1).click(bt_more).perform()
            sleep(3)
        except Exception as e:
            print(str(e))
            print('bt more not find!')
            break
    for el in flats:
        house_, section_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', '', ''
        # Дом
        try:
            text = el.find_element(By.XPATH, './div/p[1]/span[2]').text.strip()
            house_ = text.split(',')[0].strip()
            section_ = text.split(',')[1].strip()
            floor_ = text.split(',')[2].split('этаж')[0].strip()
            flat_ = text.split(',')[3].split('№')[1].strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [house_, section_, floor_, flat_]", str(e))
        # Тип
        try:
            type_ = el.find_element(By.XPATH, './div/p[1]').text
            type_ = type_.split(' ')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [type_]", str(e))
        # Площадь
        try:
            area_ = el.find_element(By.XPATH, './div/p[1]/span[1]').text.strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [area_]", str(e))
        # Цена
        try:
            price_ = el.find_element(By.XPATH, './div/p[2]/span[1]').text.strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [price_]", str(e))

        row = [house_, section_, floor_, flat_, type_, area_, price_]
        parser.add_row_info(row)

    return data
