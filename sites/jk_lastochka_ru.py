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
SITE_NAME = 'ЖК Ласточка'
SITE_URL = 'https://lasto4ka.ru/select/floor/14/84#flat'
SPREADSHEET_ID = '1Rvi72o61pjeKnDLkvMYn4iHG0t3x4P_pxmDU31pUM8Y'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1OE4pKlJrO6nwQWSqEb8XgxAVzzz8WXIatF5o7nl63dY'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Этаж', 'Квартира', 'Площадь', 'Цена']

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
                els = self.driver.get_elements((By.CSS_SELECTOR, '#main > div.container.fill-height.ma-0.pa-0 > '
                                                                 'div.v-image.v-responsive.theme--light > '
                                                                 'div.v-responsive__content > div > div > div:nth-child('
                                                                 '1)'))
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
    els = driver.get_elements((By.CSS_SELECTOR, '#main > div.container.fill-height.ma-0.pa-0 > '
                                                'div.v-image.v-responsive.theme--light > div.v-responsive__content > '
                                                'div > div > div:nth-child(1)'))
    parser.info_msg(f'Этажи: {len(els)}')
    rng = len(els)
    for floor in range(1, rng + 1, 1):
        if not app.run:
            return None
        url = f'https://lasto4ka.ru/select/floor/{floor}#floor'
        driver.get_page(url)
        sleep(2)
        els = driver.get_elements((By.CSS_SELECTOR, '#floor > div.ma-0 > div.container.flat-select.container--fluid > '
                                                    'div > div > div.v-responsive__content > svg > polygon.flat'))
        parser.info_msg(f'Этаж: {floor + 1}')
        parser.info_msg(f'Квартир: {len(els)}')
        for i in range(0, len(els), 1):
            action = webdriver.ActionChains(driver.driver)
            action.move_to_element(els[i]).click().perform()
            sleep(2)
            row = [floor + 1]
            flat, area, price = '', '', ''
            try:
                text = driver.get_element((By.CSS_SELECTOR, '#flat > div.container.pa-5 > h1')).text
                flat = text.split(' ')[0].strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [квартира]', str(e))
            try:
                area = driver.get_element((By.CSS_SELECTOR, '#flat > div.container.pa-5 > div.row.pt-5.justify-center '
                                                            '> div.col-md-4.col > '
                                                            'div.v-list.v-sheet.theme--light.v-list--dense > '
                                                            'div:nth-child(2) > div:nth-child(2) > span')).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [площадь]', str(e))
            try:
                price = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#flat > div.container.pa-5 > div.row.pt-5.justify-center > div.col-md-4.col > '
                     'div.v-list.v-sheet.theme--light.v-list--dense > div:nth-child(3) > '
                     'div.v-list-item__content.font-weight-bold')).text.strip()
                price = price.split("\n")[0]
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [цена]', str(e))
            row.extend([flat, area, price])
            parser.add_row_info(row, floor + 1, flat)
            driver.driver.back()
            sleep(1)
            els = driver.get_elements(
                (By.CSS_SELECTOR, '#floor > div.ma-0 > div.container.flat-select.container--fluid > '
                                  'div > div > div.v-responsive__content > svg > polygon.flat'))

    return data


