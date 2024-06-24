from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from cffi.backend_ctypes import unicode
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
SITE_NAME = 'ЖК Южный'
SITE_URL = 'https://xn--f1aajcq8fsa.xn--p1ai/#/macrocatalog/complex/objects/6105529?studio=null&geo_city=1868' \
           '&floorNum=1&category=flat&activity=sell&presMode=complex '
SPREADSHEET_ID = '15T4TIaYzV-o3s-IrM32d4rGaGPrhFtiP3ifbZGnxgSo'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1j6gjrMJFXNE1iQLqF6win-KX0dosSCC-kCuAxPn-YwE'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', 'Тип', '№ квартиры', 'Площадь', 'Цена']

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
            for i in range(5):
                sleep(10)
                sel = '#main-wrapper > div.current-view > div.current-view-sides > div.current-view-right > ' \
                      'div.current-view-content > div > div > div.simplebar-wrapper > div.simplebar-mask > div > div ' \
                      '> div > div > div > table > tbody > tr '
                self.driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
                els = self.driver.get_elements((By.CSS_SELECTOR, sel))
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
    sel = '#main-wrapper > div.current-view > div.current-view-sides > div.current-view-right > ' \
          'div.current-view-content > div > div > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div ' \
          '> div > table > tbody > tr '
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    els = []
    while True:
        if not app.run:
            return None
        els_ = driver.get_elements((By.CSS_SELECTOR, sel))
        webdriver.ActionChains(driver.driver).move_to_element(els_[-5]).pause(1).perform()
        sleep(3)
        if len(els_) == len(els):
            break
        els = els_
    print(f"квартир: {len(els)}")
    for el in els:
        if not app.run:
            return None
        house_, floor_, type_, flat_, area_, price_ = "", "", "", "", "", ""
        try:
            price_ = el.find_element(By.XPATH, "./td[9]/div/div/span").text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [price_]', str(e))
        if '₽' in price_:
            try:
                house_ = el.find_element(By.XPATH, "./td[2]").text.strip()
                house_ = house_.split('дом')[1].strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [house_]', str(e))
            try:
                floor_ = el.find_element(By.XPATH, "./td[6]").text.strip().replace('⁨', '').replace('⁩', '')
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [floor_]', str(e))
            try:
                type_ = el.find_element(By.XPATH, "./td[4]").text.strip().replace('⁨', '').replace('⁩', '')
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [type_]', str(e))
            try:
                flat_ = el.find_element(By.XPATH, "./td[3]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flat_]', str(e))
            try:
                area_ = el.find_element(By.XPATH, "./td[5]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [area_]', str(e))
            row = [house_, floor_, type_, flat_, area_, price_]
            parser.add_row_info(row)
    return data
