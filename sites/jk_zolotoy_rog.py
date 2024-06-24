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
SITE_NAME = 'ЖК Золотой рог'
SITE_URL = 'https://ewss-zolotoyrog.ru/flats'
SPREADSHEET_ID = '1NuyIJvUqPB-BrZtis-4A-AYqMktgFKPXQR9xg7SC9fM'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1CpAYJc9iLdL9UFvtd4zDncPx40UUp3Y1rsTM8Rzd2Hs'  # мой
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
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=False)
            self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((
            #         By.CSS_SELECTOR,
            #         '#AppWrapper > div > div > div > div.styles__Wrapper-sc-n9odu4-1.bnsRkD > '
            #         'div.styles__Results-sc-n9odu4-4.tpPsg > div > div.styles__Container-sc-1m93mro-1.jPNZOV > div > '
            #         'div > div > a'))
            #     if not els or len(els) == 0:
            #         sleep(uniform(1, 5))
            #         self.driver.close()
            #         self.driver = WebDriver(headless=HEADLESS)
            #         self.driver.get_page(SITE_URL)
            #     else:
            #         break
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
    driver_1 = WebDriver(headless=HEADLESS, wait_full_page_download=True)

    while True:
        if not app.run:
            return None
        sel = 'main > div > ul.src-components-production-Flats-blocks-MoniqueType1-List-wrapper-svn3 > li > a'
        driver.waiting_for_element((By.CSS_SELECTOR, sel), 30)
        els = driver.get_elements((
            By.CSS_SELECTOR, sel))
        print(len(els))
        try:
            bt = driver.get_element(
                (By.CSS_SELECTOR,
                 'main > div > button.src-components-production-Flats-loadMoreButton-1ilT'))
            # print(bt)
            webdriver.ActionChains(driver.driver).move_to_element(bt).pause(1).click(bt).perform()
            sleep(1)
            # break
        except Exception as e:
            print('more bt click:', str(e))
            break
    parser.info_msg(f'Квартиры: {len(els)}')

    sleep(5)
    for el in els:
        if not app.run:
            return None
        url = el.get_attribute('href')
        # print(url)
        driver_1.get_page(url)
        sleep(1)
        park_, block_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', '', ''
        # Корпус
        try:
            driver_1.waiting_for_element((By.XPATH, '//main/aside/div/div/div/div/div/ul/li[1]/div'), 30)
            park_ = driver_1.get_element((By.XPATH, '//main/aside/div/div/div/div/div/ul/li[1]/div')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [корпус]', str(e))
        # Секция
        try:
            block_ = driver_1.get_element((By.XPATH, '//main/aside/div/div/div/div/div/ul/li[2]/div')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [секция]', str(e))
        # Этаж
        try:
            floor_ = driver_1.get_element((By.XPATH, '//main/aside/div/div/div/div/div/ul/li[3]/div')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [этаж]', str(e))
        # Квартира
        try:
            flat_ = driver_1.get_element((By.XPATH, '//main/aside/div/div/header/div/div[1]/div[1]/div')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [квартира]', str(e))
        # Тип
        try:
            type_ = driver_1.get_element((By.XPATH, '//main/aside/div/div/header/div/div[1]/h2')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [тип]', str(e))
        # Площадь
        try:
            area_ = driver_1.get_element((By.XPATH, '//main/aside/div/div/header/div/div[1]/div[2]/h1')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [площадь]', str(e))
        # Цена
        try:
            price_ = driver_1.get_element((By.XPATH, '//main/aside/div/div/div/div/header/div/div/div/div')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [цена]', str(e))
        row = [park_, block_, floor_, flat_, type_, area_, price_]
        parser.add_row_info(row)
    driver_1.close()

    return data

