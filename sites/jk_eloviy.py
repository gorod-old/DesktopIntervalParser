from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from WinSoundPack import beep
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Еловый'
SITE_URL = 'https://xn----ctbhbvklle0k.xn--p1ai/'
SPREADSHEET_ID = '1oDsPgMfTYxTIcB2BbZRH3eJZNImVSMBwDvv-6sGqVvQ'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1hKbtDClL1tk_I4LpTddpBjnXX98RF2xYF1g4q-QuymE'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Название ЖК', 'Дом', 'Этаж', '№ квартиры', 'Тип', 'Площадь', 'Цена']

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
            #     els = self.driver.get_elements((
            #         By.CSS_SELECTOR,
            #         '#AppWrapper > div > div > div > div.styles__Wrapper-sc-n9odu4-1.bnsRkD > '
            #         'div.styles__Results-sc-n9odu4-4.tpPsg > div > div.styles__Container-sc-1m93mro-1.jPNZOV > div > '
            #         'div > div > a'))
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
    selector = '#sbs-429122385-1648544977147 > a'
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    bt = driver.get_element((By.CSS_SELECTOR, selector))
    bt.click()
    sleep(3)
    selector = '#profitbase_front_widget'
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    iframe = driver.get_element((By.CSS_SELECTOR, selector))
    driver.driver.switch_to.frame(iframe)
    sleep(3)
    selector = 'body > app-root > app-catalog > app-stock > div > main > app-projects > ' \
               'div.stock__panel.ng-star-inserted > app-tabs > app-desktop-tabs > section > p-tabmenu > div > ul > ' \
               'li:nth-child(3) > a > div > label '
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    bt = driver.get_element((By.CSS_SELECTOR, selector))
    bt.click()
    sleep(3)
    while True:
        if not app.run:
            return None
        selector = '#pr_id_5-table > tbody > tr'
        els = driver.get_elements((By.CSS_SELECTOR, selector))
        parser.info_msg(f'Квартиры: {len(els)}')
        rng = len(els)
        for i in range(0, rng, 1):
            if not app.run:
                return None
            el = els[i]
            obj_, house_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', '', ''
            try:
                obj_ = el.find_element(By.XPATH, "./td[2]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [obj_]', str(e))
            try:
                house_ = el.find_element(By.XPATH, "./td[3]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [house_]', str(e))
            try:
                floor_ = el.find_element(By.XPATH, "./td[10]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [floor_]', str(e))
            try:
                flat_ = el.find_element(By.XPATH, "./td[4]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flat_]', str(e))
            try:
                type_ = el.find_element(By.XPATH, "./td[1]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [type_]', str(e))
            try:
                area_ = el.find_element(By.XPATH, "./td[5]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [area_]', str(e))
            try:
                price_ = el.find_element(By.XPATH, "./td[7]").text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [price_]', str(e))
            row = [obj_, house_, floor_, flat_, type_, area_, price_]
            parser.add_row_info(row)

        selector = 'body > app-root > app-catalog > app-stock > div > main > app-projects > div.stock__content > ' \
                   'app-properties-table > app-desktop-properties-table > div > div.desktop-properties__paginator > ' \
                   'p-paginator > div > button.p-ripple.p-element.p-paginator-next.p-paginator-element.p-link '
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
        next = driver.get_element((By.CSS_SELECTOR, selector))
        if next.is_enabled():
            next.click()
            sleep(3)
        else:
            print('end')
            break
    return data
