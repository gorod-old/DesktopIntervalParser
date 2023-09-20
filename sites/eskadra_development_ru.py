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
SITE_NAME = 'ЖК "Атмосфера"'
SITE_URL = 'https://atmosferavl.ru/#visual'
# SITE_URL = 'https://www.farpost.ru/vladivostok/realty/sell_flats/?constructionStatus[]=delivered&page=1'
SPREADSHEET_ID = '128PrfeWxOpEvYmZ1imHkK6KOOTvfm3ggjbpxDduxs8s'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1l69nz3ZnKccITNfC2dOQkr9uhUPZETBvIFPjNQHMyyo'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Объект', 'Квартира', 'Этаж', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=False, window_height=3000)
            self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((By.CSS_SELECTOR, '#flats_cont > div.flats.cleaner > div.item > a'))
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
    selector = "#visual > div.selectByParams > a"
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    bt = driver.get_element((By.CSS_SELECTOR, selector))
    bt.click()
    sleep(5)
    selector = "ul.aparts > li"
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
    els_ = driver.get_elements((By.CSS_SELECTOR, selector))
    parser.info_msg(f'Квартиры: {len(els_)}')
    for el in els_:
        if not app.run:
            return None
        webdriver.ActionChains(driver.driver).move_to_element_with_offset(el, 50, 100).pause(1).perform()
        row = []
        obj, flat, floor, square, price = '', '', '', '', ''
        try:
            obj = el.find_element(By.XPATH, './div/span[2]/span[1]').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [obj]', str(e))
        try:
            flat = el.find_element(By.XPATH, './div/span[3]').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [flat]', str(e))
        try:
            floor = el.find_element(By.XPATH, './div/span[2]/span[2]/span[2]').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [floor]', str(e))
        try:
            square = el.find_element(By.XPATH, './div/span[1]/span[1]').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [square]', str(e))
        try:
            price = el.find_element(By.XPATH, './div/span[4]').text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [price]', str(e))
        row.extend([obj, flat, floor, square, price])
        parser.add_row_info(row)
    return data

    # selector_ = "#bulletins > div.pager.infinite > a"
    # driver.waiting_for_element((By.CSS_SELECTOR, selector_), 10)
    # next_bt = driver.get_element((By.CSS_SELECTOR, selector_))
    # num = 0
    # all_ = 0
    # while next_bt:
    #     selector = "#bulletins > div.viewport-padding-collapse > table"
    #     driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
    #     tables = driver.get_elements((By.CSS_SELECTOR, selector))
    #     num_ = len(tables)
    #     print(len(tables))
    #     if num_ > num:
    #         num += 1
    #         selector = f"#bulletins > div.viewport-padding-collapse > table:nth-child({num + 1}) > tbody > tr"
    #         driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
    #         els_ = driver.get_elements((By.CSS_SELECTOR, selector))
    #         all_ += len(els_) - 1
    #         parser.info_msg(f'Квартиры: {len(els_) - 1}')
    #         parser.info_msg(f'Всего: {all_}')
    #         try:
    #             price = els_[1].find_element(By.XPATH, './td/div/div/div[2]/div[1]/div/div[1]/div/span').text.strip()
    #             print('price:', price)
    #         except Exception as e:
    #             pass
    #     webdriver.ActionChains(driver.driver).move_to_element(next_bt).pause(1).perform()
    #     recaptcha = None
    #     try:
    #         next_bt.click()
    #         sleep(30)
    #         recaptcha = driver.get_element((By.CSS_SELECTOR, '#recaptcha-accessible-status'))
    #     except Exception as e:
    #         pass
    #     if recaptcha:
    #         driver.driver.recaptcha_v2_solver()
    #     driver.waiting_for_element((By.CSS_SELECTOR, selector_), 10)
    #     next_bt = driver.get_element((By.CSS_SELECTOR, selector_))

    # num = 0
    # all_ = 0
    # while True:
    #     num += 1
    #     driver.get_page(f"https://www.farpost.ru/vladivostok/realty/sell_flats/?constructionStatus[]=delivered&page={num}")
    #     selector = f"#bulletins > div.viewport-padding-collapse > table > tbody > tr"
    #     driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
    #     els_ = driver.get_elements((By.CSS_SELECTOR, selector))
    #     all_ += len(els_) - 1
    #     parser.info_msg(f'Квартиры: {len(els_) - 1}')
    #     parser.info_msg(f'Всего: {all_}')
    #     for el in els_:
    #         try:
    #             price = el.find_element(By.CSS_SELECTOR, 'span.price-block__price').text.strip()
    #             print('price:', price)
    #         except Exception as e:
    #             pass
    #     next_bt = None
    #     try:
    #         selector_ = "#bulletins > div.pager.infinite > a"
    #         driver.waiting_for_element((By.CSS_SELECTOR, selector_), 10)
    #         next_bt = driver.get_element((By.CSS_SELECTOR, selector_))
    #     except Exception as e:
    #         pass
    #     if next_bt is None:
    #         break
