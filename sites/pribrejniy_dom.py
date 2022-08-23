from random import uniform, choice
from time import sleep, time

import requests
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
SITE_NAME = 'ЖК "Прибрежный Дом'
SITE_URL = 'https://pribrezhny-dom.ru/kvartiry/'
SPREADSHEET_ID = '1nnBCs9SBAg-5xlFmWPaNWaBDGL87AM0ADp-kVLAFWqg'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1tP8k_sPupI240GmoXYw1IiMvY4vXGC8z-Yt6FaPva4M'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', 'Квартира', 'Комнат', 'Площадь', 'Цена']

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
            self.driver.get_page(SITE_URL)
            for i in range(5):
                els = self.driver.get_elements((By.CSS_SELECTOR, '#ajax-content > div'))
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
    # # driver.driver.maximize_window()
    urls = []
    i = 0
    while True:
        if not app.run:
            return None
        els = driver.get_elements((By.CSS_SELECTOR, '#ajax-content > div > a'))
        parser.info_msg(f'Квартир: {len(els)}, num: {i}')
        for j in range(i, len(els), 1):
            try:
                href = els[j].get_attribute('href')
                if '/#' not in href:
                    parser.info_msg(f'{href}')
                    urls.append(href)
            except Exception as e:
                err_log(SITE_NAME + " pars_data [href]", str(e))
        i = len(urls)
        bt_more = driver.get_element((By.CSS_SELECTOR, '#ajax-content > div.container.js-nex-cont > a'))
        if bt_more is None:
            break
        webdriver.ActionChains(driver.driver).move_to_element(bt_more).pause(2).click(bt_more).perform()
        # bt_more.click()
        sleep(1)
    parser.info_msg(f'Квартир: {len(urls)}')

    for url in urls:
        if not app.run:
            return None
        driver.get_page(url)
        sleep(1)
        block_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
        # Корпус
        try:
            block_ = driver.get_element(
                (By.XPATH, '/html/body/div[1]/main/div[1]/div/div/div[2]/div/div[1]/div[1]/span[2]')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [block_]", str(e))
        # Этаж
        try:
            floor_ = driver.get_element(
                (By.XPATH, '/html/body/div[1]/main/div[1]/div/div/div[2]/div/div[1]/div[4]/span[2]')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [floor_]", str(e))
        # Квартира
        try:
            flat_ = driver.get_element(
                (By.XPATH, '/html/body/div[1]/main/div[1]/div/div/div[2]/div/div[1]/div[2]/span[2]')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [flat_]", str(e))
        # Комнат
        try:
            text = driver.get_element(
                (By.XPATH, '/html/body/div[1]/main/div[1]/div/div/div[2]/div/h1')).text.strip().lower()
            type_ = text.split('квартира')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [type_]", str(e))
        # Площадь
        try:
            area_ = driver.get_element(
                (By.XPATH, '/html/body/div[1]/main/div[1]/div/div/div[2]/div/div[2]/div[1]/p')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [area_]", str(e))
        # Цена
        try:
            price_ = driver.get_element(
                (By.XPATH, '/html/body/div[1]/main/div[1]/div/div/div[2]/div/div[2]/div[2]/p')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + " pars_data [price_]", str(e))

        row = [block_, floor_, flat_, type_, area_, price_]
        parser.add_row_info(row)

    return data

