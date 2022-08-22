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
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Восточный Луч'
SITE_URL = 'https://vlzu.ru/apartments'
SPREADSHEET_ID = '1WIiT4dvlGu-TNLqyHHsM1RL15m8VRiMGp57kX7GPbpw'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1YPP7pzMZ5jaHl-2jkcO0_mJhozawBnjjTcl6JYX6O6E'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Тип', 'Площадь', 'Цена', 'Очередь']

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
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR, '#__next'))
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
    num = 0
    num_1 = 0
    i = 1
    while True:
        if not app.run:
            return None
        url = f'https://vlzu.ru/apartments?page={i}'
        driver.get_page(url)
        sleep(3)
        html = driver.driver.page_source
        soup = Bs(html, 'html.parser')
        els = soup.find_all("div", {"class": "CardBox_inner__3jq_2"})
        parser.info_msg(f'Страница: {i}, Квартиры: {len(els)}')
        if len(els) == 0:
            break
        num_1 += len(els)
        for el in els:
            if not app.run:
                return None
            href = None
            house_, floor_, flat_, type_, area_, price_, queue_ = '', '', '', '', '', '', ''
            # Очередь
            try:
                text = el.find('div', {"class": "CardBox_description__2Wp3_"}).getText(strip=True)
                queue_ = text.split('Восточный луч')[1].strip()
            except Exception as e:
                err_log(SITE_NAME + f' get_flat_info [queue_], page: {i}', str(e))
            # Цена
            try:
                price = el.find('div', {"class": "CardBox_price__2KWJD"}).getText(strip=True)
                price_ = price.split('₽')[0] + ' ₽'
            except Exception as e:
                err_log(SITE_NAME + f' get_flat_info [price_], page: {i}', str(e))
            # href
            try:
                href = el.find('a', {"class": "CardBox_link__3yLNB"})['href']
                href = 'https://vlzu.ru' + href
            except Exception as e:
                err_log(SITE_NAME + f' get_flat_info [href], page: {i}', str(e))

            if href is not None:
                driver.get_page(href)
                sleep(3)
                html_ = driver.driver.page_source
                soup_ = Bs(html_, "html.parser")
                el_ = soup_.find('ul', {"class": "ApartmentInfo_prop__192RT"})
                if el_ is not None:
                    # Дом
                    try:
                        house_ = el_.find("div", string="Номер дома").next_sibling.getText(strip=True)
                    except Exception as e:
                        err_log(SITE_NAME + f' get_flat_info [house_], page: {i}', str(e))
                    # Этаж
                    try:
                        floor_ = el_.find("div", string="Этаж").next_sibling.getText(strip=True)
                    except Exception as e:
                        err_log(SITE_NAME + f' get_flat_info [floor_], page: {i}', str(e))
                    # Квартира
                    try:
                        flat_ = el_.find("div", string="Номер квартиры").next_sibling.getText(strip=True)
                    except Exception as e:
                        err_log(SITE_NAME + f' get_flat_info [flat_], page: {i}', str(e))
                    # Тип, Площадь
                    try:
                        text = soup_.find('div', {"class": "ApartmentInfo_name__3xInL"}).getText(strip=True)
                        type_ = text.split(',')[0].strip()
                        parts = text.split(',')
                        parts.pop(0)
                        text = ','.join(parts)
                        area_ = text.split('м')[0].strip() + ' м²'
                    except Exception as e:
                        err_log(SITE_NAME + f' get_flat_info [type_, area_], page: {i}', str(e))

                    num += 1
                else:
                    parser.info_msg(f'element not find! page: {i}')
            else:
                parser.info_msg(f'href is None! page: {i}')

            row = [house_, floor_, flat_, type_, area_, price_, queue_]
            parser.add_row_info(row)
        i += 1
    parser.info_msg(f'Страниц: {i - 1}')
    print(num, num_1)
    return data
