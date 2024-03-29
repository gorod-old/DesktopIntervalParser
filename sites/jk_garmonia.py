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
SITE_URL = 'https://xn----8sbkg6adjts.xn--p1ai/projects/jk-garmony-dom1/plan_prices_dom1/'
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
            # self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements(
            #         (By.CSS_SELECTOR, '#image-map-pro-4500 > div > div.imp-ui > div > select'))
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
# @try_func
def pars_data(parser):
    data.clear()
    app = parser.app
    driver = parser.driver
    driver.driver.maximize_window()
    section_data = {
        'Дом 1': ['https://xn----8sbkg6adjts.xn--p1ai/projects/jk-garmony-dom1/plan_prices_dom1/',
                  '#image-map-pro-909 > div > div.imp-ui > div > select',
                  'image-map-pro-909'],
        'Дом 2': ['https://xn----8sbkg6adjts.xn--p1ai/projects/jk-garmony-dom2/plan_prices_dom2/',
                  '#image-map-pro-8705 > div > div.imp-ui > div > select',
                  'image-map-pro-8705'],
        'Дом 3': ['https://xn----8sbkg6adjts.xn--p1ai/plan_prices/',
                  '#image-map-pro-4500 > div > div.imp-ui > div > select',
                  'image-map-pro-4500'],
    }

    for key, val in section_data.items():
        url, selector, id_ = val[0], val[1], val[2]
        driver.get_page(url)
        sleep(3)
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
        select = Select(driver.get_element((By.CSS_SELECTOR, selector)))

        # filter_ = ['Дом 1', 'Дом 2']
        filter_ = []

        if key not in filter_:
            for index in reversed(range(0, len(select.options) - 1)):
                try:
                    parser.info_msg(select.options[index].text)
                except Exception as e:
                    print(e)
                try:
                    select.select_by_index(index)
                    driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
                    select = Select(driver.get_element((By.CSS_SELECTOR, selector)))
                    sleep(2)
                    print('select:', select)
                except Exception as e:
                    print(e)

                # Квартиры
                els = []
                try:
                    flat_sel = f"#{id_} > div > div.imp-zoom-outer-wrap > div > div > div.imp-shape-container > svg > " \
                               f"polygon "
                    driver.waiting_for_element((By.CSS_SELECTOR, flat_sel), 10)
                    els = driver.get_elements(
                        (By.CSS_SELECTOR, flat_sel))
                except Exception as e:
                    print(e)
                parser.info_msg(f'Квартир: {len(els)}')
                for el in els:
                    fill = ''
                    try:
                        fill = el.value_of_css_property("fill")
                    except Exception as e:
                        print(e)
                    # print('fill:', fill)
                    if fill == 'rgba(0, 255, 0, 0.4)' or fill == 'rgba(208, 255, 208, 0.4)' \
                            or fill == 'rgba(0, 255, 0, 0.29)':
                        webdriver.ActionChains(driver.driver).move_to_element(el).perform()
                        webdriver.ActionChains(driver.driver).move_by_offset(-400, 0).click().perform()
                        webdriver.ActionChains(driver.driver).move_to_element(el).click().perform()
                        sleep(1)
                        house_, floor_, flat_, area_, price_ = key, '', '', '', ''
                        # Этаж, Квартира
                        try:
                            text = driver.get_element(
                                (By.CSS_SELECTOR, "body > div.imp-tooltips-container > "
                                                  "div.imp-tooltip.imp-tooltip-visible > "
                                                  "div:nth-child(3) > div.squares-element.sq-col-lg-12 > h3")).text
                            floor_ = text.split("-")[0].split(" ")[1].strip()
                            flat_ = text.split("-")[1].strip()
                        except Exception as e:
                            err_log(SITE_NAME + f' pars_data [floor_, flat_]', str(e))
                        # Площадь
                        try:
                            if key == 'Дом 3':
                                el_ = driver.get_element(
                                    (By.CSS_SELECTOR, "body > div:nth-child(1) > div.imp-tooltip.imp-tooltip-visible > "
                                                      "div:nth-child(5) > div:nth-child(2) > h3"))
                            else:
                                el_ = driver.get_element(
                                    (By.CSS_SELECTOR, "body > div:nth-child(1) > div.imp-tooltip.imp-tooltip-visible > "
                                                      "div:nth-child(5) > div:nth-child(1) > p"))
                            text = el_.text
                            area_ = text.split("-")[1].split("м")[0].strip() + "м²"
                        except Exception as e:
                            err_log(SITE_NAME + f' pars_data [area_]', str(e))
                        # Цена
                        try:
                            text = driver.get_element(
                                (By.CSS_SELECTOR, "body > div.imp-tooltips-container > "
                                                  "div.imp-tooltip.imp-tooltip-visible > "
                                                  "div:nth-child(6) > div.squares-element.sq-col-lg-12 > h3")).text
                            price_ = text.split(":")[1].strip()
                        except Exception as e:
                            err_log(SITE_NAME + f' pars_data [price_]', str(e))
                        row = [house_, floor_, flat_, area_, price_]
                        parser.add_row_info(row)
                        # sleep(1)
    return data
