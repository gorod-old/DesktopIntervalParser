from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from MessagePack.message import err_log, print_exception_msg
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК "Долина'
SITE_URL = 'https://sabaneeva22a.ru/vybrat-kvartiru/'
SPREADSHEET_ID = '1vl963a6pJsyAcMlHxX7kaMO-FNxJJDV9C1dCOUnFeNw'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1D3oFek2mZI5_ZHuSGTG5SjOuVjfm1E9a4pRC1D1Jo2o'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Этаж', 'Квартира', 'Комнат', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS, rem_warning=True)
            self.driver.get_page(SITE_URL)
            for i in range(5):
                els = self.driver.get_elements((By.XPATH, '//*[@id="building-levels"]/div[3]/div[19]/span'))
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
    # driver.driver.maximize_window()
    els = driver.get_elements((By.XPATH, '//*[@id="building-levels"]/div[3]/div/span'))
    rng = len(els)
    parser.info_msg(f'Этажи: {rng}')
    action = webdriver.ActionChains(driver.driver)
    driver_1 = WebDriver(headless=True)
    for floor in range(rng - 1, -1, -1):  # start from length - 1 to 0
        if not app.run:
            return None
        parser.info_msg(f'Этаж: {rng - floor + 1}')

        action.move_to_element(els[floor]).move_by_offset(0, 0).pause(1).perform()
        popup_text = None
        try:
            popup_text = driver.get_element((By.XPATH, '//*[@id="building-levels"]/div[4]/span[2]')).text.strip()
            parser.info_msg(popup_text)
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [popup_text]', str(e))
        if popup_text is None or '0 квартир' not in popup_text:
            action.click().perform()
            sleep(1)
            els_ = driver.get_elements((By.XPATH, '//*[@id="all-flats__wrapper"]/ul/li/a'))
            if els_ and len(els_) > 0:
                for el in els_:
                    url = el.get_attribute('href')
                    driver_1.get_page(url)
                    sleep(1)
                    floor_, flat_, type_, area_, price_ = '', '', '', '', ''
                    # Комнат, Площадь
                    try:
                        text = driver_1.get_element(
                            (By.XPATH, '/html/body/div/div[1]/div[2]/div/div[1]/div[2]/h2')).text.strip()
                        type_ = text.split(',')[0].strip()
                        area_ = text.split(',')[-1].strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [Комнат, Площадь]', str(e))
                    # Этаж
                    try:
                        floor_ = driver_1.get_element(
                            (By.XPATH, '/html/body/div/div[1]/div[2]/div/div[1]/div[2]/ul/li[2]/span[2]')).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data ["Этаж"]', str(e))
                    # Квартира
                    try:
                        flat_ = driver_1.get_element(
                            (By.XPATH, '/html/body/div/div[1]/div[2]/div/div[1]/div[2]/ul/li[1]/span[2]')).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data ["Квартира"]', str(e))
                    # Цена
                    try:
                        price_ = driver_1.get_element(
                            (By.XPATH,
                             '/html/body/div/div[1]/div[2]/div/div[1]/div[2]/ul/li[5]/span[2]')).text.strip() + ' ₽'
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data ["Цена"]', str(e))

                    row = [floor_, flat_, type_, area_, price_]
                    parser.add_row_info(row)

        driver.get_page(SITE_URL)
        els = driver.get_elements((By.XPATH, '//*[@id="building-levels"]/div[3]/div/span'))

    driver_1.close()
    return data
