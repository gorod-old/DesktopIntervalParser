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
import numpy as np

HEADLESS = True
SITE_NAME = 'жкжуравли.рф'
SITE_URL = 'https://жкжуравли.рф/houses/'
SPREADSHEET_ID = '133PhHGidcyXSqE1ZI6x4iuRUyiv4JVfyj0OCukFRe9U'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1qsHrpYgCunlzSIoxKlw0irr1CfN15CHSeJEMIkgXs84'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Секция', 'Этаж', 'Квартира', 'Площадь', 'Цена']

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
        self.driver = WebDriver(headless=HEADLESS)
        self.driver.get_page(SITE_URL)
        for i in range(5):
            els = self.driver.get_elements((By.CSS_SELECTOR, '#page > div.main_house.d-mobile-none > svg > g'))
            if not els or len(els) == 0:
                sleep(uniform(1, 5))
                self.driver.close()
                self.driver = WebDriver(headless=HEADLESS)
                self.driver.get_page(SITE_URL)
            else:
                break

    def run(self):
        self.info_msg(f'start parser: {self.name}')
        self._create_driver()
        data_ = pars_data(self)
        if data_ and len(data_) > 0:
            gspread_update(data_, HEADER, SPREADSHEET_ID, SHEET_ID)  # gspread update_sheet_data()
        self.app.parser_result(self.name, len(data), time() - self.time)
        self.app.next_parser(self.name)
        self.driver.close()
        self.quit()


@timer_func
@try_func
def pars_data(parser):
    data.clear()
    app = parser.app
    driver = parser.driver
    driver.driver.maximize_window()
    els = driver.get_elements((By.CSS_SELECTOR, '#page > div.main_house.d-mobile-none > svg > g'))
    urls_ = []
    for el in els:
        text = el.get_attribute('onclick')
        href = SITE_URL + text.split("'")[1].split("'")[0].strip()
        urls_.append(href)
    parser.info_msg(f'Дома: {len(urls_)}')
    rng = len(urls_)
    for i in range(0, rng, 1):
        if not app.run:
            return None
        driver.get_page(urls_[i])
        sleep(3)
        current_url = driver.driver.current_url
        els_ = driver.get_elements((By.CSS_SELECTOR, '#page > div.main_house.item_house > svg > g'))
        urls = []
        for el in els_:
            text = el.get_attribute('onclick')
            href = current_url + text.split("'")[1].split("'")[0].strip()
            urls.append(href)
        for url in urls:
            driver.get_page(url)
            driver.waiting_for_element((By.CSS_SELECTOR, '#page > div.menu_page.info_menu > ul > a > li > span'), 20)
            # Дом + секция + этаж
            h, s, f = '', '', ''
            try:
                el_ = driver.get_element((By.CSS_SELECTOR, '#page > div.menu_page.info_menu > ul > a > li > span'))
                text = el_.text.lower()
                h = text.split('—')[0].split('дом')[1].strip()
                s = text.split('секция')[1].split('—')[0].strip()
                f = text.split('этаж')[1].strip()
            except Exception as e:
                err_log('pars_data [Дом + секция + этаж]', str(e))
            els_f = driver.get_elements((By.CSS_SELECTOR,
                                         '#page > div.section_floor > div.section > div.rooms > div > svg > path'))
            for el in els_f:
                row = [h, s, f]
                webdriver.ActionChains(driver.driver).move_to_element(el).perform()
                price = ''
                try:
                    price = driver.get_element(
                        (By.CSS_SELECTOR, '#page > div.section_floor > div.info > div.price > span'))\
                        .text.strip()
                except Exception as e:
                    err_log('pars_data [Квартира]', str(e))
                if '- руб.' not in price:
                    flat = ''
                    try:
                        flat = driver.get_element(
                            (By.CSS_SELECTOR, '#page > div.section_floor > div.info > div.room > span'))\
                            .text.strip()
                    except Exception as e:
                        err_log('pars_data [Квартира]', str(e))
                    square = ''
                    try:
                        square = driver.get_element(
                            (By.CSS_SELECTOR, '#page > div.section_floor > div.info > div.area > span'))\
                            .text.strip()
                    except Exception as e:
                        err_log('pars_data [Квартира]', str(e))
                    row.extend([flat, square, price])
                    data.append(row)
                    parser.info_msg(row)
    return data
