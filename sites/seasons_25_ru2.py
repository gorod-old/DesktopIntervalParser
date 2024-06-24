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
SITE_URL = 'https://seasons25.ru/buy'
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
    selector = 'div.window svg rect'
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    floors = driver.get_elements((By.CSS_SELECTOR, selector))
    print(f"этажи: {len(floors)}")
    sleep(5)
    for i in range(len(floors)):
        if not app.run:
            return None
        webdriver.ActionChains(driver.driver).move_to_element(floors[i]).click().perform()
        sleep(3)
        selector_ = 'iframe.mfp-iframe'
        driver.waiting_for_element((By.CSS_SELECTOR, selector_), 30)
        iframe = driver.get_element((By.CSS_SELECTOR, selector_))
        driver.driver.switch_to.frame(iframe)
        selector_ = 'div.window svg path'
        driver.waiting_for_element((By.CSS_SELECTOR, selector_), 20)
        flats = driver.get_elements((By.CSS_SELECTOR, selector_))
        print(f"квартиры: {len(flats)}")
        for j in range(len(flats)):
            if not app.run:
                return None
            fill = flats[j].get_attribute("fill")
            if fill == "#3ba108":
                flats[j].click()
                sleep(3)
                section_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
                try:
                    text = driver.get_element(
                        (By.CSS_SELECTOR, "div.apartment-details > p")).text.strip().lower()
                    # print(text)
                    area_ = text.split('\n')[0].strip()
                    section_ = text.split('секция')[0].split(',')[1].strip()
                    floor_ = text.split('этаж')[0].split('секция')[1].strip()
                    type_ = text.split('комнат')[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [section_, area_, floor_, type_]', str(e))
                try:
                    flat_ = driver.get_element(
                        (By.CSS_SELECTOR, "div.apartment-info-box > h1")).text.lower().split("квартира")[1].split('\n')[0].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                try:
                    price_ = driver.get_element(
                        (By.CSS_SELECTOR, "div.apartment-details")).text.lower().strip().split("руб")[0].split('\n')[-1].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [price_]', str(e))
                row = [section_, floor_, flat_, type_, area_, price_]
                parser.add_row_info(row)
                driver.driver.back()
                sleep(3)
                selector_ = 'iframe.mfp-iframe'
                driver.waiting_for_element((By.CSS_SELECTOR, selector_), 30)
                iframe = driver.get_element((By.CSS_SELECTOR, selector_))
                driver.driver.switch_to.frame(iframe)
                selector_ = 'div.window svg path'
                driver.waiting_for_element((By.CSS_SELECTOR, selector_), 20)
                flats = driver.get_elements((By.CSS_SELECTOR, selector_))
        driver.driver.switch_to.default_content()
        selector_ = 'button.mfp-close'
        driver.waiting_for_element((By.CSS_SELECTOR, selector_), 30)
        close = driver.get_element((By.CSS_SELECTOR, selector_))
        close.click()
        sleep(3)
    return data



