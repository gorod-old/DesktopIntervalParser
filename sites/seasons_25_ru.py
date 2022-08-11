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
SITE_NAME = 'Времена года'
SITE_URL = 'http://seasons25.ru/buy'
SPREADSHEET_ID = '1NCoiDqAW4SrNB1OsnLg8nTqGqFjKO9NUTUeOrRRKhTU'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1TeouLI-SdiOhYP1NJpi_--ITRwuHG6eU7DMpM7WXdTA'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Секция', 'Этаж', 'Квартира', 'Площадь', 'Цена']

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
                els = self.driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > rect'))
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
    els = driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > rect'))
    parser.info_msg(f'Этажи: {len(els)}')
    rng = len(els)
    for floor in range(0, rng, 1):
        if not app.run:
            return None
        check = False
        try:
            webdriver.ActionChains(driver.driver).move_to_element(els[floor]).click().perform()
            sleep(1)
            frame = driver.get_elements((By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp'
                                                          '-ready > div > div.mfp-content > div > iframe'))[0]
            driver.driver.switch_to.frame(frame)
            el = driver.get_element((By.CSS_SELECTOR, '#blockquote > h2')).text
            d = int(el.split('секция')[0].strip())
            f = int(el.split('секция')[1].split('этаж')[0].strip())
            parser.info_msg(f'Секция: {d}, Этаж: {f}, Индекс: {floor}')
            check = True
        except Exception as e:
            # err_log('pars_data [Этаж клик]', str(e))
            pass
        if check:
            # Квартиры
            get_flat_info(driver, f, d, app, parser)
            driver.driver.switch_to.default_content()
            driver.get_page(SITE_URL)
            sleep(1)
            els = driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > rect'))
    return data


def get_flat_info(driver, floor, section, app, parser):
    hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div > div.flag-text'))
    rng = len(hints)/2
    parser.info_msg(f'Квартиры: {int(rng)}')
    for i in range(0, len(hints), 1):
        if not app.run:
            return
        text = hints[i].text
        if 'продано' not in text.lower() and 'забронировано' not in text.lower() \
                and 'посмотреть квартиру' not in text.lower():
            try:
                row = [section, floor]
                flat = text.split('квартира')[0].strip()
                square = text.split('квартира')[1].split('кв')[0].strip() + ' кв.м.'
                price = text.split('кв.м.')[1].strip()
                row.extend([flat, square, price])
                data.append(row)
                parser.info_msg(row)
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [квартира, площадь, цена]', str(e))

