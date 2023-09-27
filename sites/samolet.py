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
SITE_NAME = 'Сабанеева 125'
SITE_URL = 'https://samolet.ru/vladivostok/flats/'
SPREADSHEET_ID = '1Dq6dDCTyFMh7pP5Hxh8nNbwepDlDQchkBnWqP_QWhcY'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1rZuTN2OE3EGGRR16a9PYotNC40jzo74hXOKa9v6eERs'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Объект', 'Корпус', 'Секция', 'Квартира', 'Тип', 'Этаж', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=True, window_height=3000)
            self.driver.get_page(SITE_URL)
            for i in range(5):
                selector = "body > main > div > div > div.flats__wrapper > div > div.flats__content > div > " \
                           "div.flats-container__list-wrap > div > div > div > a "
                self.driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
                els = self.driver.get_elements((By.CSS_SELECTOR, selector))
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
    sleep(10)
    while True:
        try:
            selector = "body > main > div > div > div.flats__wrapper > div > div.flats__content > div > " \
                       "div.flats-container__more._second > button "
            driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
            bt = driver.get_element((By.CSS_SELECTOR, selector))
            webdriver.ActionChains(driver.driver).move_to_element(bt).pause(1).click(bt).perform()
        except Exception as e:
            break
    selector = "body > main > div > div > div.flats__wrapper > div > div.flats__content > div > " \
               "div.flats-container__list-wrap > div > div > div > a "
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    els = driver.get_elements((By.CSS_SELECTOR, selector))
    parser.info_msg(f'Квартиры: {len(els)}')
    urls = []
    for el in els:
        url = el.get_attribute('href')
        urls.append(url)
    print('urls:', len(urls))
    for url in urls:
        driver.get_page(url)
        selector = "body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > " \
                   "div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > div.r-flat-d-aside__info-btn "
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
        bt = driver.get_element((By.CSS_SELECTOR, selector))
        bt.click()
        sleep(1)
        row = []
        obj_, corp_, section_, flat_, type_, floor_, square_, price_ = '', '', '', '', '', '', '', ''
        try:
            obj_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > div.r-flat-d-aside__info > '
                 'div:nth-child(2) > div.r-flat-d-aside__row-val.r-flat-d-aside__row-link > a')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [obj]', str(e))
        try:
            corp_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > '
                 'div.r-flat-d-aside__info-more._active > div:nth-child(2)')).text.strip().replace('\n', ' ')
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [corp]', str(e))
        try:
            section_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > '
                 'div.r-flat-d-aside__info-more._active > div:nth-child(3)')).text.strip().replace('\n', ' ')
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [section]', str(e))
        try:
            flat_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > '
                 'div.r-flat-d-aside__info-more._active > div:nth-child(5) > '
                 'div.r-flat-d-aside__row-val')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [flat]', str(e))
        try:
            type_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > div.r-flat-d-aside__head > '
                 'div.r-flat-head > div.r-flat-head__title-wrapper > h2 > span > span:nth-child(1)')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [type]', str(e))
        try:
            floor_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > '
                 'div.r-flat-d-aside__info-more._active > div:nth-child(4) > '
                 'div.r-flat-d-aside__row-val')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [floor]', str(e))
        try:
            square_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > div.r-flat-d-aside__head > '
                 'div.r-flat-head > div.r-flat-head__title-wrapper > h2 > span > '
                 'span.r-flat-head__title-area')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [square]', str(e))
        try:
            price_ = driver.get_element(
                (By.CSS_SELECTOR,
                 'body > main > div > div.r-flat-detail__info.r-flat-detail__color > div > div > '
                 'div.r-flat-d-info__aside.js-flat-d-info-aside > div.r-flat-d-aside > div.r-flat-d-aside__head > '
                 'div.r-flat-head > div.r-flat-head__row > div.r-flat-head__row-inner > div.r-flat-head__row._mt0 > '
                 'div')).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [price]', str(e))
        row.extend([obj_, corp_, section_, flat_, type_, floor_, square_, price_])
        parser.add_row_info(row)
    return data
