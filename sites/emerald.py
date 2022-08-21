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
SITE_NAME = 'ЖК "Эмеральд'
SITE_URL = 'https://emeraldstroy.ru/'
SPREADSHEET_ID = '1W-6ElXk5ZQQUlTI47zwoMLu6i3I_-k88s2WqWzNn0Uo'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1k9lUVPvTc5y5cbHsLjs8gNO17Z4XnfWeK66Yhwc5QvY'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Этаж', 'Квартира', 'Комнат', 'Площадь', 'Цена']

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
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR, '#app > section.first-screen.position-relative > div > div > div:nth-child(2) > '
                                      'div > div.position-relative > img'))
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
    print('check')
    data.clear()
    app = parser.app
    driver = parser.driver
    # driver.driver.maximize_window()
    els = driver.get_elements((By.CSS_SELECTOR, '#app > section.first-screen.position-relative > div > div > '
                                                'div:nth-child(2) > div > div.position-relative > svg > polygon'))
    parser.info_msg(f'Этажи: {len(els)}')
    floor_urls = []
    for el in els:
        url = el.get_attribute('onclick')
        url = 'https://' + url.split('https://')[1].split("'")[0].strip()
        floor_urls.append(url)
    driver_1 = WebDriver(headless=True)
    for url in floor_urls:
        if not app.run:
            return None
        driver.get_page(url)
        sleep(1)
        els_ = driver.get_elements(
            (By.CSS_SELECTOR, '#app > div.floor > div > div.floor__plan > div.position-relative.w-fit.mx-auto > svg > '
                              'polygon'))
        parser.info_msg(f'Квартир: {len(els_)}')
        flat_urls = []
        for el in els_:
            url = el.get_attribute('onclick')
            url = 'https://' + url.split('https://')[1].split("'")[0].strip()
            flat_urls.append(url)
        for flat_url in flat_urls:
            if not app.run:
                return None
            driver_1.get_page(flat_url)
            floor_, flat_, type_, area_, price_ = '', '', '', '', ''
            # Цена
            try:
                price_ = driver_1.get_element(
                    (By.XPATH, '//*[@id="app"]/div[1]/div/div/div[2]/div[2]')).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [price_]', str(e))
            if 'руб' in price_:
                # Этваж
                try:
                    text = driver_1.get_element((By.XPATH, '//*[@id="app"]/div[1]/div/nav/ol/li[2]/a')).text.strip()
                    floor_ = text.split('Этаж')[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [floor_]', str(e))
                # Квартира
                try:
                    text = driver_1.get_element((By.XPATH, '//*[@id="app"]/div[1]/div/nav/ol/li[3]')).text.strip()
                    flat_ = text.split('Квартира')[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                # Комнат
                try:
                    type_ = driver_1.get_element(
                        (By.XPATH, '//*[@id="app"]/div[1]/div/div/div[2]/div[1]/div[3]/span[2]')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [type_]', str(e))
                # Площадь
                try:
                    area_ = driver_1.get_element(
                        (By.XPATH, '//*[@id="app"]/div[1]/div/div/div[2]/div[1]/div[1]/span[2]')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [area_]', str(e))

                row = [floor_, flat_, type_, area_, price_]
                parser.add_row_info(row)

    driver_1.close()
    return data
