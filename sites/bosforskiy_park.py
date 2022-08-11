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
SITE_NAME = 'ЖК Босфорский парк'
SITE_URL = 'https://www.pik.ru/search/vladivostok/bosforskiypark'
SPREADSHEET_ID = '1TfBj0p8pYFZc0RBaTbWz94xUIu8yQGNl2gGD5kY-s8M'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1yBwm1qTuVjth5OoFKkK8U0FTmrKZ52ZHS1dsz3BuubA'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Корпус', 'Секция', 'Этаж', '№ на этаже', 'Тип', 'Площадь', 'Цена']

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
                els = self.driver.get_elements((By.CSS_SELECTOR, '#AppWrapper > div > div > div > '
                                                                 'div.styles__Wrapper-sc-n9odu4-1.bnsRkD > '
                                                                 'div.styles__Results-sc-n9odu4-4.tpPsg > div > '
                                                                 'div.styles__Container-sc-1m93mro-1.jPNZOV > div > div > '
                                                                 'div > a'))
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
    els = driver.get_elements((By.CSS_SELECTOR, '#AppWrapper > div > div > div > '
                                                'div.styles__Wrapper-sc-n9odu4-1.bnsRkD > '
                                                'div.styles__Results-sc-n9odu4-4.tpPsg > div > '
                                                'div.styles__Container-sc-1m93mro-1.jPNZOV > div > div > div > a'))
    parser.info_msg(f'Квартиры: {len(els)}')
    driver_1 = WebDriver(headless=HEADLESS)
    for el in els:
        if not app.run:
            return None
        block_, section_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', '', ''
        # Комнат + площадь
        try:
            text = el.find_element(By.XPATH, './div[2]/p').text
            type_ = text.split(' ')[0].strip()
            area_ = text.split(' ')[1].strip() + 'м²'
        except Exception as e:
            err_log(SHEET_NAME + ' get_flat_info [тип, площадь]', str(e))
        # Корпус + секция + этаж
        try:
            text = el.find_element(By.XPATH, './div[2]/div[1]/span').text
            block_ = text.split('Корпус')[1].split('·')[0].strip()
            section_ = text.split('секция')[1].split('·')[0].strip()
            floor_ = text.split('этаж')[1].strip()
        except Exception as e:
            err_log(SHEET_NAME + ' get_flat_info [Корпус, секция, этаж]', str(e))
        # Цена
        try:
            text = el.find_element(By.XPATH, './div[3]/div/div[1]/div/div[1]/span').text
            price_ = text.strip()
        except Exception as e:
            err_log(SHEET_NAME + ' get_flat_info [Цена]', str(e))
        # № квартиры на этаже
        try:
            url = el.get_attribute('href')
            driver_1.get_page(url)
            bt = (By.XPATH, '//*[@id="InfoWrapper"]/div[1]/div/div/div/div[2]/div[1]')
            driver_1.waiting_for_element(bt, 20)
            driver_1.get_element(bt).click()
            sleep(1)
            el = (By.XPATH, '//*[@id="InfoWrapper"]/div[1]/div/div/div/div[2]/div[2]/div/div/div/div/div['
                            '6]/div[2]')
            flat_ = driver_1.get_element(el).text.strip()
        except Exception as e:
            err_log(SHEET_NAME + ' get_flat_info [№ на этаже]', str(e))
        row = [block_, section_, floor_, flat_, type_, area_, price_]
        parser.add_row_info(row)
    driver_1.close()
    return data
