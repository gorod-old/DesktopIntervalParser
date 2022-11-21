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
SITE_NAME = 'ЖК Южный'
SITE_URL = 'https://xn--f1aajcq8fsa.xn--p1ai/#/profitbase/projects/list?filter=property.status:AVAILABLE'
SPREADSHEET_ID = '15T4TIaYzV-o3s-IrM32d4rGaGPrhFtiP3ifbZGnxgSo'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1j6gjrMJFXNE1iQLqF6win-KX0dosSCC-kCuAxPn-YwE'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Площадь', 'Цена', 'Статус']

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
                self.driver.waiting_for_element((By.XPATH, '//*[@id="profitbase_front_widget"]'), 20)
                els = self.driver.get_elements((By.XPATH, '//*[@id="profitbase_front_widget"]'))
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
    frame = driver.get_element((By.XPATH, '//*[@id="profitbase_front_widget"]'))
    driver.driver.switch_to.frame(frame)
    driver.waiting_for_element((By.XPATH, ".//p-paginator/div/button[contains(@class, 'p-paginator-next')]"), 20)
    disabled, next_bt, page = False, None, 1
    sleep(5)
    while not disabled:
        if not app.run:
            return None
        if next_bt:
            next_bt.click()
            sleep(1)
        sleep(uniform(1, 1.5))
        els = driver.get_elements((By.XPATH, ".//div[contains(@id, 'pr_id')]/div/table/tbody/tr"))
        parser.info_msg(f"page: {page}, els: {len(els)}")
        for el in els:
            if not app.run:
                return None
            type_ = el.find_element(By.XPATH, ".//td[9]").text.strip()
            if type_.lower() == "квартира":
                house_, floor_, flat_, area_, price_, status_ = "", "", "", "", "", ""
                try:
                    house_ = el.find_element(By.XPATH, ".//td[3]").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [house_]', str(e))
                try:
                    floor_ = el.find_element(By.XPATH, ".//td[10]").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [floor_]', str(e))
                try:
                    flat_ = el.find_element(By.XPATH, ".//td[4]").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                try:
                    area_ = el.find_element(By.XPATH, ".//td[5]").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [area_]', str(e))
                try:
                    price_ = el.find_element(By.XPATH, ".//td[7]").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [price_]', str(e))
                try:
                    status_ = el.find_element(By.XPATH, ".//td[8]/div").text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [status_]', str(e))
                row = [house_, floor_, flat_, area_, price_, status_]
                parser.add_row_info(row)

        next_bt = driver.get_element((By.XPATH, ".//p-paginator/div/button[contains(@class, 'p-paginator-next')]"))
        print(next_bt)
        print(next_bt.get_attribute("class"))
        disabled = "p-disabled" in next_bt.get_attribute("class")
        page += 1

    return data
