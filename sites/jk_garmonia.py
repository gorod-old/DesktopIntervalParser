from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Гармония'
SITE_URL = 'https://xn----8sbkg6adjts.xn--p1ai/jk-garmonia-3/#block1'
SPREADSHEET_ID = '1TMofHMKhxCknqLQusUpH1X4r9zuZlmmDUT5UUQQpjVs'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1RaCJZAzaI01EDlXyC4wMj0iQj-KTVuI_esu1F8-WhKM'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Площадь', 'Цена']

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
                    (By.CSS_SELECTOR, '#image-map-pro-4500 > div > div.imp-ui > div > select'))
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

    select = Select(driver.get_element((By.CSS_SELECTOR, "#image-map-pro-4500 > div > div.imp-ui > div > select")))

    for index in reversed(range(0, len(select.options) - 1)):
        parser.info_msg(select.options[index].text)
        select.select_by_index(index)
        driver.waiting_for_element((By.CSS_SELECTOR, "#image-map-pro-4500 > div > div.imp-ui > div > select"), 10)
        select = Select(driver.get_element((By.CSS_SELECTOR, "#image-map-pro-4500 > div > div.imp-ui > div > select")))
        sleep(1)

        # Квартиры
        els = driver.get_elements(
            (By.CSS_SELECTOR, "#image-map-pro-4500 > div > div.imp-zoom-outer-wrap > div > div > "
                              "div.imp-shape-container > svg > polygon"))
        parser.info_msg(f'Квартир: {len(els)}')
        for el in els:
            fill = el.value_of_css_property("fill")
            if fill == 'rgba(0, 255, 0, 0.29)' or fill == 'rgba(208, 255, 208, 0.4)':
                webdriver.ActionChains(driver.driver).move_to_element(el).click().perform()
                sleep(1)
                house_, floor_, flat_, area_, price_ = '3', '', '', '', ''
                # Этаж, Квартира
                try:
                    text = driver.get_element(
                        (By.CSS_SELECTOR, "body > div.imp-tooltips-container > div.imp-tooltip.imp-tooltip-visible > "
                                          "div:nth-child(3) > div.squares-element.sq-col-lg-12 > h3")).text
                    floor_ = text.split("-")[0].split(" ")[1].strip()
                    flat_ = text.split("-")[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + f' pars_data [floor_, flat_]', str(e))
                # Площадь
                try:
                    el_ = driver.get_element(
                        (By.CSS_SELECTOR, "body > div.imp-tooltips-container > div.imp-tooltip.imp-tooltip-visible > "
                                          "div:nth-child(5) > div:nth-child(2) > h3"))
                    if el_ is None:
                        el_ = driver.get_element(
                            (By.CSS_SELECTOR,
                             "body > div.imp-tooltips-container > div.imp-tooltip.imp-tooltip-visible > "
                             "div:nth-child(5) > div:nth-child(3) > h3"))
                    text = el_.text
                    area_ = text.split("-")[1].split("м")[0].strip() + "м²"
                except Exception as e:
                    err_log(SITE_NAME + f' pars_data [area_]', str(e))
                # Цена
                try:
                    text = driver.get_element(
                        (By.CSS_SELECTOR, "body > div.imp-tooltips-container > div.imp-tooltip.imp-tooltip-visible > "
                                          "div:nth-child(6) > div.squares-element.sq-col-lg-12 > h3")).text
                    price_ = text.split(":")[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + f' pars_data [price_]', str(e))
                row = [house_, floor_, flat_, area_, price_]
                parser.add_row_info(row)
                webdriver.ActionChains(driver.driver).move_by_offset(-500, 0).perform()

    return data
