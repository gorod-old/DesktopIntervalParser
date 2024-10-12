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
SITE_NAME = 'ЖК Андерсен'
SITE_URL = 'https://domoplaner.ru/catalog/397/1SnVMq/chess/?house_id=2383'
SPREADSHEET_ID = '19OSRJXlVTLaYy_ysXvjaVL1jcf3394SY125EFA9ffQk'  # заказчика
SHEET_ID = 1484614729  # заказчика
SHEET_NAME = 'parser'  # заказчика
# SPREADSHEET_ID = ''  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Тип', 'Площадь', 'Цена']

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
            # for i in range(5):
            #     els = self.driver.get_elements(
            #         (By.CSS_SELECTOR, '#__next'))
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
    sleep(5)
    urls = []
    selector = 'body > div > section > div.sw-flex > div.sw-left.g-left.global-left-color > ' \
               'div.std-menu.custom-scrollbar.ng-scope > div.std-menu-type.global-left-color.--chess.ng-scope.active ' \
               '> div > div > a '
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
    els = driver.get_elements((By.CSS_SELECTOR, selector))
    for el in els:
        url = el.get_attribute('href')
        urls.append(url)
        print(url)
    i = 0
    while i < len(urls):
        if not app.run:
            return None
        if i > 0:
            driver.get_page(urls[i])
            sleep(5)
        selector = '#chess-sph-table div.spht-flat2.ng-scope.cell-free'
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
        els = driver.get_elements((By.CSS_SELECTOR, selector))
        parser.info_msg(f"Квартиры: {len(els)}")
        for el in els:
            if not app.run:
                return None
            webdriver.ActionChains(driver.driver).move_to_element(el).perform()
            el.click()
            sleep(1)
            house_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
            try:
                xpath = '/html/body/div[1]/div/div/section/div/div/div/div[1]/div/div[1]/div[3]/div[2]/div[6]/div[' \
                        '2]/span '
                house_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [house_]', str(e))
            try:
                xpath = '/html/body/div[1]/div/div/section/div/div/div/div[1]/div/div[1]/div[3]/div[2]/div[5]/div[' \
                        '2]/span '
                floor_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [floor_]', str(e))
            try:
                xpath = '/html/body/div[1]/div/div/section/div/div/div/div[1]/div/div[1]/div[3]/div[2]/div[4]/div[' \
                        '2]/span '
                flat_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flat_]', str(e))
            try:
                xpath = '/html/body/div[1]/div/div/section/div/div/div/div[1]/div/div[1]/div[3]/div[2]/div[2]/div[' \
                        '2]/span '
                type_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [type_]', str(e))
            try:
                xpath = '/html/body/div[1]/div/div/section/div/div/div/div[1]/div/div[1]/div[3]/div[2]/div[3]/div[' \
                        '2]/span '
                area_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [area_]', str(e))
            try:
                xpath = '/html/body/div[1]/div/div/section/div/div/div/div[1]/div/div[1]/div[3]/div[2]/div[1]/div[' \
                        '1]/div[2]/span/strong '
                price_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [price_]', str(e))

            row = [house_, floor_, flat_, type_, area_, price_]
            parser.add_row_info(row)

            selector = 'body > div.modal.flatModal.ng-scope.ng-isolate-scope.in > div > div > section > div > div > ' \
                       'button '
            driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
            close = driver.get_element((By.CSS_SELECTOR, selector))
            close.click()
            sleep(1)
        i += 1
    return data
