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
SITE_NAME = 'ЖК "Кленовый'
SITE_URL = 'https://klenovyi.ru/floors/etazh-1'
SPREADSHEET_ID = '1IjfdIH5qQA0Qq76_fruof5EGrzLjnbj8jjuNbPF62gc'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1-26bKEy_-Qa_ih_qkTgC5K6bkqhLTR_PpIBNgzmcj2k'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Этаж', 'Квартира', 'Комнат', 'Площадь', 'Цена', 'Статус']

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
                els = self.driver.get_elements((By.XPATH, '/html/body/div[1]/main/div/div[2]/div/div[2]/div/ul/li'))
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
    els = driver.get_elements((By.XPATH, '/html/body/div[1]/main/div/div[2]/div/div[2]/div/ul/li'))
    parser.info_msg(f'Этажи: {len(els) - 2}')
    rng = len(els) - 1
    for floor in range(1, rng, 1):  # start from 1
        if not app.run:
            return None
        parser.info_msg(f'Этаж: {floor}')
        url = f'https://klenovyi.ru/floors/etazh-{floor}'
        driver.get_page(url)
        sleep(2)
        els_ = driver.get_elements((By.CSS_SELECTOR, 'svg > polygon.Polygonable__polygon'))
        parser.info_msg(f'Квартир: {len(els_)}')
        try:
            map_ = driver.get_element((By.XPATH, '/html/body/div[1]/main/div/div[2]/div/div[1]/div/div/div'))
            driver.driver.execute_script("arguments[0].scrollIntoView(false);", map_)
            sleep(3)

            offset = 150

            action = webdriver.ActionChains(driver.driver)
            action.move_to_element_with_offset(map_, 600, 150 + offset).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)

            action = webdriver.ActionChains(driver.driver)
            action.move_to_element_with_offset(map_, 320, 150 + offset).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
            action.move_by_offset(-10, 100).pause(1).perform()
            get_flat_info(parser, driver)
        except Exception as e:
            err_log(SITE_NAME + ' pars_data', str(e))
    return data


def get_flat_info(parser, driver):
    text = None
    try:
        text = driver.get_element(
            (By.XPATH, '/html/body/div[1]/main/div/div[2]/div/div[1]/div/div/div/div/div/div')).text.strip()
    except Exception as e:
        err_log(SITE_NAME + ' get_flat_info [text]', str(e))
    # print(text)
    floor_, flat_, type_, area_, price_, status_ = '', '', '', '', '', ''
    if text is None or text == '':
        parser.info_msg('text not find!')
        return
    # Статус
    try:
        status_ = text.split('\n')[1].split('Этаж:')[0].strip()
    except Exception as e:
        err_log(SITE_NAME + ' get_flat_info [status_]', str(e))
    if 'Свободна' in status_:
        # Этаж
        try:
            floor_ = text.split('Этаж:')[1].split('Количество комнат:')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [floor_]', str(e))
        # Квартира
        try:
            flat_ = text.split('Квартира')[1].split('\n')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [flat_]', str(e))
        # Комнат
        try:
            type_ = text.split('Количество комнат:')[1].split('Площадь квартиры:')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [type_]', str(e))
        # Площадь
        try:
            area_ = text.split('Площадь квартиры:')[1].split('Сторона света:')[0].strip()
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [area_]', str(e))
        # Цена
        try:
            if 'Цена:' in text:
                price_ = text.split('Цена:')[1].split('₽')[0].strip() + ' ₽'
        except Exception as e:
            err_log(SITE_NAME + ' get_flat_info [price_]', str(e))

        row = [floor_, flat_, type_, area_, price_, status_]
        parser.add_row_info(row)
