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
SITE_NAME = 'ЖК "Домино'
SITE_URL = 'https://xn----htbekhoifd.xn--p1ai/house'
SPREADSHEET_ID = '1sUPVMLfCt5QuOzYa0tqS0e8gdYECU7Vs3UXH2dI5UGk'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1XJVNmvn_c9k1kvQsU0rSCwrJc-C4Y5jwnof0oYm3hyQ'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Подъезд', 'Этаж', 'Квартира', 'Комнат', 'Площадь', 'Цена', 'Статус']

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
            # self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((By.CSS_SELECTOR, 'div.window > div > svg > path'))
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
    # driver.driver.maximize_window()
    entrances = 3
    floors = 8
    for i in range(1, entrances + 1, 1):  # start from 1
        parser.info_msg(f'Подъезд: {i}')
        for j in range(1, floors + 1, 1):  # start from 1
            if not app.run:
                return None
            parser.info_msg(f'Этаж: {j}')
            url = f'https://xn----htbekhoifd.xn--p1ai/apartments?entrance={i}&floor={j}'
            driver.get_page(url)
            try:
                if i == 1:
                    map_ = driver.get_element((By.XPATH, '/html/body/div[1]/main/div[1]/div/section/div[1]/div'))
                    driver.driver.execute_script("arguments[0].scrollIntoView(false);", map_)
                    sleep(3)

                    offset_x = 0
                    offset_y = 0

                    action = webdriver.ActionChains(driver.driver)
                    action.move_to_element_with_offset(map_, 200 + offset_x, 300 + offset_y).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(340, 0).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(50, 0).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(340, 0).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                elif i == 2:
                    map_ = driver.get_element((By.XPATH, '/html/body/div[1]/main/div[1]/div/section/div[1]/div'))
                    driver.driver.execute_script("arguments[0].scrollIntoView(false);", map_)
                    sleep(3)

                    offset_x = 20
                    offset_y = 200

                    action = webdriver.ActionChains(driver.driver)
                    action.move_to_element_with_offset(map_, 200 + offset_x, 300 + offset_y).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(300, 0).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(50, 0).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(320, 0).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                elif i == 3:
                    map_ = driver.get_element((By.XPATH, '/html/body/div[1]/main/div[1]/div/section/div[1]/div'))
                    driver.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", map_)
                    sleep(3)

                    offset_x = 0
                    offset_y = 0

                    action = webdriver.ActionChains(driver.driver)
                    action.move_to_element_with_offset(map_, 300 + offset_x, 300 + offset_y).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(0, 280).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(0, 70).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
                    action.move_by_offset(0, 300).pause(1).perform()
                    get_flat_info(parser, driver, i, j)
            except Exception as e:
                err_log(SITE_NAME + ' pars_data', str(e))

    return data


def get_flat_info(parser, driver, d, f):
    text = None
    try:
        text = driver.get_element(
            (By.XPATH, '/html/body/div[1]/main/div[1]/div/section/div[1]/div/div')).text.strip()
    except Exception as e:
        # err_log(SITE_NAME + ' get_flat_info [text]', str(e))
        pass
    # print(text)
    entrance_, floor_, flat_, type_, area_, price_, status_ = '', '', '', '', '', '', ''
    entrance_ = d
    floor_ = f
    if text is None or text == '':
        parser.info_msg('text not find!')
        return
    # Статус
    try:
        status_ = text.split('\n')[1].split('Комнат')[0].strip()
    except Exception as e:
        err_log(SITE_NAME + ' get_flat_info [status_]', str(e))
    if 'Свободна' in status_:
        # Квартира
        try:
            flat_ = text.split('Квартира')[1].split('\n')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [flat_]', str(e))
        # Комнат
        try:
            type_ = text.split('Комнат:')[1].split('Площадь')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [type_]', str(e))
        # Площадь
        try:
            area_ = text.split('Площадь:')[1].split('Цена')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [area_]', str(e))
        # Цена
        try:
            if 'Цена:' in text:
                price_ = text.split('Цена:')[1].split('₽')[0].strip() + ' ₽'
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [price_]', str(e))

        row = [entrance_, floor_, flat_, type_, area_, price_, status_]
        parser.add_row_info(row)
