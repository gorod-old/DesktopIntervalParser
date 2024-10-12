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
SITE_NAME = 'ЖК Five'
SITE_URL = 'https://five-dom.ru/#/catalog/house/120334/list?floorNumber=14&filter=property.status:AVAILABLE'
SPREADSHEET_ID = '12bhYuZA0kHsHpGoe7DFxS6ANdopnY7qCWri6mjWQI70'  # заказчика
SHEET_ID = 2088640919  # заказчика
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
    sleep(10)
    sel = 'body > sw-wrapper > iframe'
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    iframe = driver.get_element((By.CSS_SELECTOR, sel))
    print(iframe)
    driver.driver.switch_to.frame(iframe)
    sleep(1)
    while True:
        if not app.run:
            return None
        selector = 'tbody > tr'
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
        els_ = driver.get_elements((By.CSS_SELECTOR, selector))
        print(len(els_))
        for el in els_:
            if not app.run:
                return None
            house_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
            try:
                xpath = './td[5]'
                house_ = el.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [house_]', str(e))
            try:
                xpath = './td[10]'
                floor_ = el.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [floor_]', str(e))
            try:
                xpath = './td[6]'
                flat_ = el.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flat_]', str(e))
            try:
                xpath = './td[3]'
                type_ = el.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [type_]', str(e))
            try:
                xpath = './td[7]'
                area_ = el.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [area_]', str(e))
            try:
                xpath = './td[9]'
                price_ = el.find_element(By.XPATH, xpath).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [price_]', str(e))

            row = [house_, floor_, flat_, type_, area_, price_]
            parser.add_row_info(row)

        selector = 'pb-paginator > div > div > button:last-child'
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
        bt_next = driver.get_element((By.CSS_SELECTOR, selector))
        print('bt_next: ', bt_next)
        disabled = bt_next.get_attribute('disabled')
        print(disabled)
        if disabled == 'true':
            break
        else:
            bt_next.click()
            sleep(5)

    return data
