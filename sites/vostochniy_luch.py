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
SITE_URL = 'https://vlsz.ru/project/pobeda#/macrocatalog/complexes/3302200?studio=null&category=flat&activity=sell'
SPREADSHEET_ID = '1Kj-aK06iriMxoJABe9bybReDmflFaR73G2ajMiAjJbg'  # заказчика
SHEET_ID = 206119309  # заказчика
SHEET_NAME = 'parser'  # заказчика
# SPREADSHEET_ID = '1YPP7pzMZ5jaHl-2jkcO0_mJhozawBnjjTcl6JYX6O6E'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Подъезд', 'Этаж', '№ квартиры', 'Тип', 'Площадь', 'Цена']

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
                selector = '#main-wrapper > div > div.current-view-sides > div.current-view-right > ' \
                           'div.current-view-content > div > div > div > div > div.simplebar-wrapper > ' \
                           'div.simplebar-mask > div > div > div > div > div > ' \
                           'a > div > div.house_other > div.house_title '
                els = self.driver.get_elements(
                    (By.CSS_SELECTOR, selector))
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
    sleep(5)
    selector = '#main-wrapper > div > div.current-view-sides > div.current-view-right > div.current-view-content > ' \
               'div > div > div > div > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div > ' \
               'a > div > div.house_other > div.house_title '
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
    els = driver.get_elements((By.CSS_SELECTOR, selector))
    els[0].click()
    sleep(5)
    selector = '#main-wrapper > div > div.current-view-sides > div.current-view-right > div.filters-navigation > div ' \
               '> div > li:nth-child(6) > a '
    tab = driver.get_element((By.CSS_SELECTOR, selector))
    tab.click()
    sleep(5)
    n = 2
    while True:
        if not app.run:
            return None
        selector = '#main-wrapper > div > div.macro-widget-navigation > ' \
                   'div.catalog-dropdown.widgets-nav-complexes.dropdown '
        select = driver.get_element((By.CSS_SELECTOR, selector))
        select.click()
        selector = '#main-wrapper > div > div.macro-widget-navigation > ' \
                   'div.catalog-dropdown.widgets-nav-complexes.dropdown.opened > div:nth-child(2) > ul > li '
        items = driver.get_elements((By.CSS_SELECTOR, selector))
        house_, entrance_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', '', ''
        if n < len(items):
            try:
                house_ = items[n].text.strip()
                print(house_)
            except Exception as e:
                err_log(SITE_NAME + ' pars_data [house_]', str(e))
            items[n].click()
            n += 1
            sleep(5)
            els_ = []
            num, i = 0, 0
            while True:
                if not app.run:
                    return None
                if i >= len(els_):
                    sel = '#main-wrapper > div > div.current-view-sides > div.current-view-right > ' \
                          'div.current-view-content > div > div > div > div > div > div.simplebar-wrapper > ' \
                          'div.simplebar-mask > div > div > div > div.all-objects-cont.in-house > div > table > tbody ' \
                          '> tr '
                    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
                    els_ = driver.get_elements((By.CSS_SELECTOR, sel))
                    if len(els_) > num:
                        num = len(els_)
                    else:
                        break
                webdriver.ActionChains(driver.driver).move_to_element(els_[i]).perform()
                sleep(1)
                try:
                    xpath = './td[7]/div/div/span'
                    price_ = els_[i].find_element(By.XPATH, xpath).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [price_]', str(e))
                if '₽' in price_:
                    try:
                        xpath = './td[6]/a'
                        entrance_ = els_[i].find_element(By.XPATH, xpath).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [entrance_]', str(e))
                    try:
                        xpath = './td[5]'
                        floor_ = els_[i].find_element(By.XPATH, xpath).text.replace('⁨', '').replace('⁩', '').strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [floor_]', str(e))
                    try:
                        xpath = './td[4]'
                        area_ = els_[i].find_element(By.XPATH, xpath).text.replace('м²', '').strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [area_]', str(e))
                    try:
                        xpath = './td[3]'
                        type_ = els_[i].find_element(By.XPATH, xpath).text.replace('⁨', '').replace('⁩', '').strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [type_]', str(e))
                    try:
                        xpath = './td[2]/div/span'
                        flat_ = els_[i].find_element(By.XPATH, xpath).text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                    row = [house_, entrance_, floor_, flat_, type_, area_, price_]
                    parser.add_row_info(row)
                i += 1
        else:
            break
    return data
