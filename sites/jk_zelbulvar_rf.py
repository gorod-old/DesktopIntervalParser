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
SITE_NAME = 'ЖК "Зеленый Бульвар"'
SITE_URL = 'https://xn--80abdkakqodr2b6a9gsa.xn--p1ai/reservation/'
SPREADSHEET_ID = '1Gl8EIYxxaeivCVHmGgD7EpIqUbHO2RlEHpQ5Ieem6js'  # заказчика
SHEET_ID = 985137872  # заказчика
SHEET_NAME = 'Лист2'  # заказчика
# SPREADSHEET_ID = '1gx_dCPMI_2ygTqxcnMMY_MGnSEjcDerwaFOqPTYlbgI'  # мой
# SHEET_ID = 1548802859  # мой
# SHEET_NAME = 'Лист5'  # мой
HEADER = ['Дом', 'Этаж', 'Квартира', 'Тип', 'Площадь', 'Статус', 'Цена']

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
        self.driver = WebDriver(headless=HEADLESS)
        self.driver.get_page(SITE_URL,
                             element=(By.CSS_SELECTOR, '#reservation-complex__svg > svg'),
                             el_max_wait_time=20)
        for i in range(5):
            els = self.driver.get_elements((By.CSS_SELECTOR, '#reservation-complex__svg > svg'))
            if not els or len(els) == 0:
                sleep(uniform(1, 5))
                self.driver.close()
                self.driver = WebDriver(headless=HEADLESS)
                self.driver.get_page(SITE_URL,
                                     element=(By.CSS_SELECTOR, '#reservation-complex__svg > svg'),
                                     el_max_wait_time=20)
            else:
                break

    def run(self):
        self.info_msg(f'start parser: {self.name}')
        self._create_driver()
        data_ = pars_data(self)
        if data_ and len(data_) > 0:
            gspread_update(data_, HEADER, SPREADSHEET_ID, SHEET_ID)  # gspread update_sheet_data()
        self.app.parser_result(self.name, len(data), time() - self.time)
        self.app.next_parser(self.name)
        self.driver.close()
        self.quit()


@timer_func
@try_func
def pars_data(parser):
    data.clear()
    app = parser.app
    driver = parser.driver
    driver.driver.maximize_window()
    # second tab for extract price
    driver.driver.execute_script("window.open('');")
    driver.driver.switch_to.window(driver.driver.window_handles[1])
    driver.get_page(SITE_URL,
                    element=(By.CSS_SELECTOR, '#reservation-complex__svg > svg'),
                    el_max_wait_time=20)
    sleep(3)
    # price button
    price_bt = driver.get_element((By.CSS_SELECTOR, '#new-filter-button'))
    price_bt.click()
    # reset button
    reset_bt = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-clean'))
    # find button
    find_bt = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-submit'))
    # house numbers
    numbers = []
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(4) > div '
                                              '> div:nth-child(1)'))
    numbers.append(el)
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(4) > div '
                                              '> div:nth-child(2)'))
    numbers.append(el)
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(4) > div '
                                              '> div:nth-child(3)'))
    numbers.append(el)
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(4) > div '
                                              '> div:nth-child(4)'))
    numbers.append(el)
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(4) > div '
                                              '> div:nth-child(5)'))
    numbers.append(el)
    # flat types
    types = []
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(5) > div '
                                              '> div:nth-child(1)'))
    types.append(el)
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(5) > div '
                                              '> div:nth-child(2)'))
    types.append(el)
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(5) > div '
                                              '> div:nth-child(3)'))
    types.append(el)
    el = driver.get_element((By.CSS_SELECTOR, '#reservation-filters-form > div:nth-child(1) > div:nth-child(5) > div '
                                              '> div:nth-child(4)'))
    types.append(el)
    driver.driver.switch_to.window(driver.driver.window_handles[0])

    # Этажи
    els = driver.get_elements((By.CSS_SELECTOR, '#reservation-complex__svg > svg > path'))
    parser.info_msg(f'Этажи: {len(els)}')
    webdriver.ActionChains(driver.driver).click().perform()
    action = webdriver.ActionChains(driver.driver)
    action.move_to_element(els[1]).click(els[1]).perform()
    action.reset_actions()
    sleep(3)
    h = 1  # номер дома
    i = 2  # индекс этажа
    f = 2  # этаж
    k = 1  # индекс квартиры

    # i = 118
    # k = 124
    # h = 5
    # f = 17
    while i <= len(els):
        if not app.run:
            return None
        if i == 26 or i == 52 or i == 77 or i == 102:
            f = 3 if i == 102 else 2
            i = i + 2 if i == 102 else i + 1
            h += 1
            k = 1
        url = f'https://xn--80abdkakqodr2b6a9gsa.xn--p1ai/reservation/#M{h}/{f}'
        driver.get_page(
            url, element=
            (By.CSS_SELECTOR,
             '#reservation-level > div > div.reservation__navigation > div > h2 > span'),
            el_max_wait_time=10)
        sleep(1)
        # Квартиры
        if h == 5:
            els_ = driver.get_elements((By.CSS_SELECTOR, '#reservation-level > div > div.glide > div > ul > li > div > '
                                                         'div.reservation-level__svg > svg > polygon'))
        else:
            els_ = driver.get_elements((By.CSS_SELECTOR, '#reservation-level > div > div.glide > div > ul > li > div > '
                                                         'div.reservation-level__svg > svg > path'))
        # driver.waiting_for_element(
        #     (By.CSS_SELECTOR, '#reservation-level > div > div.reservation__navigation > div > h2 > span'), 10)
        action = webdriver.ActionChains(driver.driver)
        action.move_to_element(els_[0]).click().perform()
        action.reset_actions()
        parser.info_msg(f'Дом: {h} Этаж (индекс): {i}')
        j = 1
        repeat = 0
        while j < 15:
            if not app.run:
                return None
            if h < 4 and f == 2 and j == 13:
                break
            elif h < 4 and j == 14:
                break
            elif h == 4 and f < 13 and j == 14:
                break
            elif h == 5 and f < 6 and j == 4:
                break
            elif h == 5 and j == 11:
                break
            if j > 1:
                url = f'https://xn--80abdkakqodr2b6a9gsa.xn--p1ai/reservation/#M{h}/{f}/{k}'
                driver.get_page(
                    url, element=
                    (By.CSS_SELECTOR,
                     '#reservation-flat > div > div.reservation-flat__info > ul:nth-child(4) > li:nth-child(3)'),
                    el_max_wait_time=10)
            sleep(uniform(2.0, 3.0))
            if repeat > 0:
                sleep(2 * repeat)
            house_, floor_, flat_, type_, area_, status_, price_ = '', '', '', '', '', '', ''
            # Дом
            house_ = h
            # Этаж
            floor_ = f
            # Квартира
            try:
                txt = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#reservation-flat > h2')).text
                flat_ = txt.split('Квартира №')[1].strip()
            except Exception as e:
                err_log('get_flat_info [квартира]', str(e))
            # Тип Квартиры
            try:
                txt = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#reservation-flat > div > div.reservation-flat__info > ul:nth-child(4) > li:nth-child(2)')).text
                type_ = txt.split('Тип квартиры:')[1].strip()
            except Exception as e:
                err_log('get_flat_info [тип квартиры]', str(e))
            # Площадь
            try:
                txt = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#reservation-flat > div > div.reservation-flat__info > ul:nth-child(4) > li:nth-child(3)')).text
                area_ = txt.split('Площадь квартиры: ')[1].strip()
            except Exception as e:
                err_log('get_flat_info [площадь]', str(e))
            # Статус
            try:
                status_ = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#reservation-flat > div > div.reservation-flat__info > ul:nth-child(4) >'
                     ' li:nth-child(1) > span')).text.strip()
            except Exception as e:
                err_log('get_flat_info [статус]', str(e))
            # Цена
            price_ = '- ₽'
            try:
                txt = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#reservation-flat > div > div.reservation-flat__info > '
                     'ul:nth-child(4) > li:nth-child(5)')).text
                price_ = txt.split('Стоимость квартиры:')[1].strip()
                if status_ == 'СВОБОДНА' and price_ == '- ₽':
                    driver.driver.switch_to.window(driver.driver.window_handles[1])
                    sleep(2)
                    numbers[h - 1].click()
                    sleep(2)
                    t = 0 if str(type_).upper() == 'СТУДИЯ' else int(type_)
                    types[t].click()
                    sleep(2)
                    find_bt.click()
                    sleep(2)
                    tab_els = driver.get_elements(
                        (By.CSS_SELECTOR, '#reservation-result__content > tr > td:nth-child(6)'))
                    index = None
                    for n, el in enumerate(tab_els):
                        text = el.text.strip()
                        if text == flat_:
                            index = n
                    if index is not None:
                        tab_els = driver.get_elements(
                            (By.CSS_SELECTOR, '#reservation-result__content > tr > td:nth-child(3)'))
                        price_ = tab_els[int(index)].text.strip()
                    numbers[h - 1].click()
                    sleep(2)
                    types[t].click()
                    sleep(2)
                    reset_bt.click()
                    driver.driver.switch_to.window(driver.driver.window_handles[0])
            except Exception as e:
                err_log('get_flat_info [статус]', str(e))
                print('Не удалось получить цену!')
            row = [house_, floor_, flat_, type_, area_, status_, price_]
            if (len(row) == 0 or '' in row) and repeat < 3:
                repeat += 1
            else:
                parser.add_row_info(row, i, j)
                j += 1
                k += 1
                repeat = 0
        i += 1
        f += 1
    return data

