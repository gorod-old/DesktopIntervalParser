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
SITE_URL = 'http://seasons25.ru'
SPREADSHEET_ID = '1NCoiDqAW4SrNB1OsnLg8nTqGqFjKO9NUTUeOrRRKhTU'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1TeouLI-SdiOhYP1NJpi_--ITRwuHG6eU7DMpM7WXdTA'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Секция', 'Этаж', 'Квартира', 'Тип', 'Площадь', 'Цена']

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
    selector = '#n2-ss-4 > div > div.n2-ss-slider-2.n2-ow > div > ' \
               'div.n2-ss-slide.n2-ss-canvas.n2-ow.n2-ss-slide-49.n2-ss-slide-active > div > div > div > ' \
               'div:nth-child(3) > div > div > div > div > div > div > a '
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    bt = driver.get_element((By.CSS_SELECTOR, selector))
    sleep(5)
    bt.click()
    sleep(5)
    driver.waiting_for_element((By.CSS_SELECTOR, '#target-frame-d8wa8gfa9f'), 20)
    iframe = driver.get_element((By.CSS_SELECTOR, '#target-frame-d8wa8gfa9f'))
    driver.driver.switch_to.frame(iframe)
    selector = 'body > div > section > div.sw-flex > div.sw-left.g-left.global-left-color > ' \
               'div.std-menu.custom-scrollbar.ng-scope > div.std-menu-type.global-left-color.--chess.ng-scope > a '
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    bt = driver.get_element((By.CSS_SELECTOR, selector))
    bt.click()
    sleep(5)
    selector = '#chess-sph-table > div > div.spht-floors2 > div > div > div.spht-flat2.ng-scope.cell-free'
    els = driver.get_elements((By.CSS_SELECTOR, selector))
    parser.info_msg(f'Квартиры: {len(els)}')
    rng = len(els)
    for i in range(0, rng, 1):
        if not app.run:
            return None
        try:
            webdriver.ActionChains(driver.driver).move_to_element(els[i]).click().perform()
            sleep(3)
            section_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
            try:
                section_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div.sphs-subinner > div.sphs-text > div.sphsi-params > div:nth-child(6) "
                                      "> div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [section_]', str(e))
            try:
                floor_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div.sphs-subinner > div.sphs-text > div.sphsi-params > div:nth-child(5) "
                                      "> div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [floor_]', str(e))
            try:
                flat_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div.sphs-subinner > div.sphs-text > div.sphsi-params > div:nth-child(4) "
                                      "> div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flat_]', str(e))
            try:
                type_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div.sphs-subinner > div.sphs-text > div.sphsi-params > div:nth-child(2) "
                                      "> div.sphsi-param-value.ng-scope > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [type_]', str(e))
            try:
                area_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div.sphs-subinner > div.sphs-text > div.sphsi-params > div:nth-child(3) "
                                      "> div.sphsi-param-value > span")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [area_]', str(e))
            try:
                price_ = driver.get_element(
                    (By.CSS_SELECTOR, "body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section "
                                      "> div > div > div > div.flat-panel-data-container.ng-scope.ng-isolate-scope > "
                                      "div > div.sphs-subinner > div.sphs-text > div.sphsi-params > div:nth-child(1) "
                                      "> div:nth-child(1) > div.sphsi-param-value.ng-scope > span > "
                                      "strong")).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [price_]', str(e))
            row = [section_, floor_, flat_, type_, area_, price_]
            parser.add_row_info(row)

            selector = 'body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section > div > div > ' \
                       'button '
            driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
            back = driver.get_element((By.CSS_SELECTOR, selector))
            back.click()
            sleep(5)
        except Exception as e:
            # err_log('pars_data [Этаж клик]', str(e))
            pass
    return data


