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
SITE_NAME = 'ЖК Сингапур'
SITE_URL = 'http://xn----ftbfngwbfoh.xn--p1ai/singapur-1-1st-floor.html'
SPREADSHEET_ID = '164PiFwhhYCSmNOQ3iIr-Msh0P8cEMFLrvfJPlNG5wpM'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1U6ry0vxy0rw_oygKGY9b1zvX8GFgiN1wIdTZmO0pkeg'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Площадь', 'Комнат', 'Цена']

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
                    (By.CSS_SELECTOR,
                     '#bigText > div.map > svg > a > path'), 20)
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR,
                     '#bigText > div.map > svg > a > path'))
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

    for complex_ in range(1, 4):
        for floor_ in range(1, 25):
            if not app.run:
                return None
            driver.get_page(f"http://xn----ftbfngwbfoh.xn--p1ai/singapur-{complex_}-{floor_}st-floor.html")
            driver.waiting_for_element(
                (By.CSS_SELECTOR,
                 '#bigText > div.map > svg > a > path'), 20)
            els = driver.get_elements(
                (By.CSS_SELECTOR,
                 '#bigText > div.map > svg > a > path'))
            parser.info_msg(f"комплекс: {complex_}, этаж: {floor_}, квартиры: {len(els)}")

            check = None
            for el in els:
                if not app.run:
                    return None
                fill = el.get_attribute("fill")
                if fill == '#ccff90':
                    webdriver.ActionChains(driver.driver).move_to_element(el).click(el).perform()
                    sleep(1)

                    house_, floor_, flat_, area_, rooms_, price_ = f"{complex_}", f"{floor_}", "", "", "", ""
                    try:
                        flat_ = driver.get_element((
                            By.XPATH,
                            '//span[@class="nomer"]')).text.strip()
                        if flat_ == '' or (check is not None and check == flat_):
                            if flat_ == '':
                                webdriver.ActionChains(driver.driver)\
                                    .move_to_element_with_offset(el, 90, 90).click().perform()
                            else:
                                webdriver.ActionChains(driver.driver) \
                                    .move_to_element_with_offset(el, 150, 90).click().perform()

                            flat_ = driver.get_element((
                                By.XPATH,
                                '//span[@class="nomer"]')).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                    try:
                        area_ = driver.get_element((
                            By.XPATH,
                            '//*[@id="fullRoom"]/div/div[2]/div[2]/div/ul/li[div[contains(text(), '
                            '"Общая площадь")]]/div[2]/span')).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [area_]', str(e))
                    try:
                        rooms_ = driver.get_element((
                            By.XPATH,
                            '//*[@id="fullRoom"]/div/div[2]/div[2]/div/ul/li[div[contains(text(), '
                            '"Количество комнат")]]/div[2]/span')).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [rooms_]', str(e))
                    try:
                        price_ = driver.get_element((
                            By.XPATH,
                            '//*[@id="zena"]')).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [price_]', str(e))

                    row = [house_, floor_, flat_, area_, rooms_, price_]
                    parser.add_row_info(row)
                    check = flat_
        #     break
        # break
    return data
