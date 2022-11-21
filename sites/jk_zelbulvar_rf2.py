from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from MessagePack.message import err_log, print_info_msg
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК "Зеленый Бульвар"'
SITE_URL = 'https://xn--80abdkakqodr2b6a9gsa.xn--p1ai/podbor-kvartir/'
SPREADSHEET_ID = '1Gl8EIYxxaeivCVHmGgD7EpIqUbHO2RlEHpQ5Ieem6js'  # заказчика
SHEET_ID = 985137872  # заказчика
SHEET_NAME = 'Лист2'  # заказчика
# SPREADSHEET_ID = '15jkM1TG1c3y4Wg-v8-wCRpYAod5zjxJUZUbyqsftlw4'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', 'Квартира', 'Площадь', 'Цена']

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
            self.driver.get_page(SITE_URL,
                                 element=(By.CSS_SELECTOR, "#svgcontent > a.scheme-houses"),
                                 el_max_wait_time=20)

            for i in range(5):
                els = self.driver.get_elements((By.CSS_SELECTOR, '#svgcontent > a.scheme-houses'))
                if not els or len(els) == 0:
                    sleep(uniform(1, 5))
                    self.driver.close()
                    self.driver = WebDriver(headless=HEADLESS)
                    self.driver.get_page(SITE_URL,
                                         element=(By.CSS_SELECTOR, "#svgcontent > a.scheme-houses"),
                                         el_max_wait_time=20)
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
    driver1 = WebDriver(headless=HEADLESS)
    driver.driver.maximize_window()
    sleep(10)
    els_ = driver.get_elements((By.CSS_SELECTOR, "#svgcontent > a.scheme-houses"))
    print("houses:", len(els_))
    for h in range(1, len(els_) + 1):
        if not app.run:
            return None
        try:
            href = els_[h - 1].get_attribute("href")["baseVal"]
        except Exception as e:
            href = None
            print_info_msg(f"[house {h} href val] " + str(e))
        if href is not None:
            print("Дом:", h)
            url = SITE_URL + href
            driver1.get_page(url, element=(
                By.CSS_SELECTOR,
                f'#reservation-complex > div > div > div.section.scheme-houses.scheme-house-{h} > div'),
                             el_max_wait_time=20)

            els = driver1.get_elements(
                (By.CSS_SELECTOR,
                 f"#reservation-complex > div > div > div.section.scheme-houses.scheme-house-{h} > a"))
            print("floors:", len(els))
            for el in els:
                if not app.run:
                    return None
                url = el.get_attribute("href")
                print("url:", url)
                selector = '#reservation-level div.reservation-level__svg > svg > path' if h != 5 \
                    else '#Слой_1 > polygon'
                driver1.get_page(url, element=(By.CSS_SELECTOR, selector),
                                 el_max_wait_time=20)
                sleep(3)
                flat_els = driver1.get_elements((By.CSS_SELECTOR, selector))

                for f_el in flat_els:
                    reserved = "reservation-item-reserved" in f_el.get_attribute("class")
                    if not reserved:
                        floor = url.split("/")[-1]
                        flat = f_el.get_attribute("data-number")
                        area = f_el.get_attribute("data-area")
                        price = f_el.get_attribute("data-price") + " ₽"
                        row = [h, floor, flat, area, price]
                        parser.add_row_info(row, h, floor)
    return data
