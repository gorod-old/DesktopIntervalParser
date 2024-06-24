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
SITE_NAME = 'ЖК Старк'
SITE_URL = 'https://domoplaner.ru/catalog/383/8I59Ck/chess/?house_id=2322'
SPREADSHEET_ID = '1-gUVURgK434eC1B6CFZnc20t-F97qY0YD3aGN1j1QLs'  # заказчика
SHEET_ID = 405111200  # заказчика
SHEET_NAME = 'Лист2'  # заказчика
# SPREADSHEET_ID = ''  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Башня', 'Этаж', 'Квартира', 'Тип', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=True)
            self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > rect'))
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
    selector = 'div.sw-left.g-left.global-left-color > div.std-menu.custom-scrollbar.ng-scope > ' \
               'div.std-menu-type.global-left-color.--chess.ng-scope.active > div > div > a '
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    h_bts = driver.get_elements((By.CSS_SELECTOR, selector))
    print(f"дома: {len(h_bts)}")
    sleep(5)
    for j in range(len(h_bts)):
        if not app.run:
            return None
        h_bts[j].click()
        sleep(3)
        for i in range(10):
            selector_ = '#chess-sph-table div.spht-flat2.ng-scope.cell-free'
            driver.waiting_for_element((By.CSS_SELECTOR, selector_), 20)
            flats = driver.get_elements((By.CSS_SELECTOR, selector_))
            print(f"квартиры: {len(flats)}")
            if len(flats) > 0:
                break
            else:
                driver.driver.refresh()
                driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
                h_bts = driver.get_elements((By.CSS_SELECTOR, selector))
                print(f"дома: {len(h_bts)}")
        else:
            flats = []
        # i = 0
        for flat in flats:
            # i += 1
            # if i == 11:
            #     break
            webdriver.ActionChains(driver.driver).move_to_element(flat).click().perform()
            sleep(3)
            section_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
            try:
                section_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div > div.sphs-text > div.sphsi-params > div:nth-child(6) > "
                                      "div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [section_]', str(e))
            try:
                floor_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div > div.sphs-text > div.sphsi-params > div:nth-child(5) > "
                                      "div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [floor_]', str(e))
            try:
                flat_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div > div.sphs-text > div.sphsi-params > div:nth-child(4) > "
                                      "div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flat_]', str(e))
            try:
                type_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div > div.sphs-text > div.sphsi-params > div:nth-child(2) > "
                                      "div.sphsi-param-value.ng-scope > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [type_]', str(e))
            try:
                area_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div > div.sphs-text > div.sphsi-params > div:nth-child(3) > "
                                      "div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [area_]', str(e))
            try:
                price_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div > div.sphs-text > div.sphsi-params > div:nth-child(1) > "
                                      "div:nth-child(1) > div.sphsi-param-value.ng-scope > span > "
                                      "strong")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [price_]', str(e))
            row = [section_, floor_, flat_, type_, area_, price_]
            parser.add_row_info(row)
            driver.driver.back()

    return data



