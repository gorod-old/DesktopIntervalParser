from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from MessagePack.message import err_log, print_exception_msg
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Панорама'
SITE_URL = 'https://panorama-vl.ru/#visual'
SPREADSHEET_ID = '1iHXobAxFZN_PVyNqs-kmp2Sndhu6vOciaih7wmLPidY'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1fv1SlMv51B4OmXcNJyVo-_P1HN_kszOmdira3VAxzCo'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Площадь', 'Комнат', 'Цена']

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
            self.driver.get_page(SITE_URL, )
            for i in range(5):
                sleep(3)
                self.driver.waiting_for_element((By.CSS_SELECTOR, '#top > a.btn.btn-lg.defaultBtn.selectApart'), 20)
                els = self.driver.get_elements((By.CSS_SELECTOR, '#top > a.btn.btn-lg.defaultBtn.selectApart'))
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
    driver.waiting_for_element((By.CSS_SELECTOR, '#visualSvg > path'), 20)
    els = driver.get_elements((By.CSS_SELECTOR, '#visualSvg > path'))
    parser.info_msg(f"этажи: {len(els)}")
    if len(els) > 0:
        webdriver.ActionChains(driver.driver).move_to_element(els[0]).pause(2).click(els[0]).perform()
        sleep(3)
        for i in range(24):
            if not app.run:
                return None
            els_ = []
            try:
                els_ = driver.get_elements((By.CSS_SELECTOR, '#floorSvg > foreignObject'))
                parser.info_msg(f"квартиры: {len(els_)}")
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flats]', str(e))

            for el in els_:
                if not app.run:
                    return None
                webdriver.ActionChains(driver.driver).move_to_element_with_offset(el, 0, -5).pause(1).perform()
                tooltip = driver.get_element((By.CSS_SELECTOR, '#flatTip'))
                if "свободно" in tooltip.text.strip().lower():
                    house_, floor_, flat_, area_, rooms_, price_ = '', '', '', '', '', ''
                    house_ = "1 корпус"
                    floor_ = i + 2
                    try:
                        flat_ = tooltip.find_element(By.CSS_SELECTOR, "span.flatNumber").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                    try:
                        rooms_ = tooltip.find_element(
                            By.CSS_SELECTOR,
                            "span.flatRooms").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [rooms_]', str(e))
                    try:
                        area_ = tooltip.find_element(
                            By.CSS_SELECTOR,
                            "span.flatArea").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [area_]', str(e))
                    try:
                        price_ = tooltip.find_element(
                            By.CSS_SELECTOR,
                            "div.tipRow.priceRow > span").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [price_]', str(e))
                    row = [house_, floor_, flat_, area_, rooms_, price_]
                    parser.add_row_info(row)
            try:
                up = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#floorFullContent > div.box > div.controls > div.group1 > div.floorSelect > div.selectBox > '
                     'svg.svg_icon.control_up'))
                up.click()
                sleep(1)
            except Exception as e:
                pass
        close = driver.get_element((By.CSS_SELECTOR, "#loadFloorModal > div > div > div.modal-header > svg"))
        close.click()
        webdriver.ActionChains(driver.driver).move_to_element(els[24]).pause(2).click(els[24]).perform()
        sleep(3)
        for i in range(22):
            if not app.run:
                return None
            els_ = []
            try:
                els_ = driver.get_elements((By.CSS_SELECTOR, '#floorSvg > foreignObject'))
                parser.info_msg(f"квартиры: {len(els_)}")
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [flats]', str(e))

            for el in els_:
                if not app.run:
                    return None
                webdriver.ActionChains(driver.driver).move_to_element_with_offset(el, 0, -5).pause(1).perform()
                tooltip = driver.get_element((By.CSS_SELECTOR, '#flatTip'))
                if "свободно" in tooltip.text.strip().lower():
                    house_, floor_, flat_, area_, rooms_, price_ = '', '', '', '', '', ''
                    house_ = "2 корпус"
                    floor_ = i + 4
                    try:
                        flat_ = tooltip.find_element(By.CSS_SELECTOR, "span.flatNumber").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                    try:
                        rooms_ = tooltip.find_element(
                            By.CSS_SELECTOR,
                            "span.flatRooms").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [rooms_]', str(e))
                    try:
                        area_ = tooltip.find_element(
                            By.CSS_SELECTOR,
                            "span.flatArea").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [area_]', str(e))
                    try:
                        price_ = tooltip.find_element(
                            By.CSS_SELECTOR,
                            "div.tipRow.priceRow > span").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [price_]', str(e))
                    row = [house_, floor_, flat_, area_, rooms_, price_]
                    parser.add_row_info(row)
            try:
                up = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#floorFullContent > div.box > div.controls > div.group1 > div.floorSelect > div.selectBox > '
                     'svg.svg_icon.control_up'))
                up.click()
                sleep(1)
            except Exception as e:
                pass

    return data

