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
SITE_NAME = 'ЖК Босфорский парк'
SITE_URL = 'https://www.pik.ru/vladivostok/projects?zoom=12&latitude=43.127438922073146&longitude=131.95268362670487' \
           '&geoBox=43.03986485524069,43.21488689599415-131.83183401732987,132.07353323607987 '
SPREADSHEET_ID = '1TfBj0p8pYFZc0RBaTbWz94xUIu8yQGNl2gGD5kY-s8M'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1yBwm1qTuVjth5OoFKkK8U0FTmrKZ52ZHS1dsz3BuubA'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Комплекс', 'Блок', 'Этаж', '№ на этаже', 'Тип', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=False)
            self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((
            #         By.CSS_SELECTOR,
            #         '#AppWrapper > div > div > div > div.styles__Wrapper-sc-n9odu4-1.bnsRkD > '
            #         'div.styles__Results-sc-n9odu4-4.tpPsg > div > div.styles__Container-sc-1m93mro-1.jPNZOV > div > '
            #         'div > div > a'))
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
    driver.driver.maximize_window()
    # driver_1 = WebDriver(headless=HEADLESS, wait_full_page_download=False)

    while True:
        selector = '#projectList > div > a'
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
        links = driver.get_elements(
            (By.CSS_SELECTOR, selector))
        parser.info_msg(f'Комплексы: {len(links)}')
        urls, names = [], []
        for i, lnk in enumerate(links):
            try:
                href = lnk.get_attribute('href')
                urls.append(href)
                name = lnk.find_element(By.XPATH, './div[2]/div[1]/h2').text
                names.append(name)
            except Exception as e:
                print('error')
                pass
        if len(urls) == len(links) and len(names) == len(links):
            break
        else:
            driver.driver.refresh()

    parser.info_msg(f'Ссылки: {urls}')
    parser.info_msg(f'Названия: {names}')

    for i, url in enumerate(urls):
        driver.get_page(url)

        while True:
            selector = '#project_filter_submit_button'
            driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
            bt = driver.get_element((By.CSS_SELECTOR, selector))
            try:
                bt.click()
                break
            except Exception as e:
                print('get flat bt click error')
                driver.driver.refresh()

        driver.driver.switch_to.window(driver.driver.window_handles[-1])
        while True:
            if not app.run:
                return None
            sel = '#SearchList > div > div:nth-child(1) > div > div > div > a'
            driver.waiting_for_element((By.CSS_SELECTOR, sel), 30)
            els = driver.get_elements((By.CSS_SELECTOR, sel))
            # print(len(els))
            try:
                bt = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#SearchList > div > div:nth-child(2) > div > div > button'))
                webdriver.ActionChains(driver.driver).move_to_element(bt).pause(1).click(bt).perform()
                sleep(3)
                # break
            except Exception as e:
                print('more bt click:', str(e))
                break
        parser.info_msg(f'Квартиры: {len(els)}')

        sleep(5)
        for el in els:
            if not app.run:
                return None
            park_, block_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', '', ''
            park_ = names[i]
            # Комнат + площадь
            try:
                text = el.find_element(By.XPATH, './div[2]/div[1]/div[1]/div[1]').text
                type_ = text.split(', ')[0].strip()
                area_ = text.split(', ')[1].strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [тип, площадь]', str(e))
            # Корпус + этаж
            try:
                text = el.find_element(By.XPATH, './div[2]/div[2]/div[3]/span[1]').text
                block_ = text.split('Корпус')[1].split(',')[0].strip()
                floor_ = text.split('Этаж')[1].strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [Корпус, этаж]', str(e))
            # Цена
            try:
                text = el.find_element(By.XPATH, './div[2]/div[2]/div[1]/div[1]/div').text
                price_ = text.strip().replace('от ', '')
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [Цена]', str(e))
            # № квартиры на этаже
            webdriver.ActionChains(driver.driver).move_to_element(el).pause(1).click(el).perform()
            sleep(1)
            driver.driver.switch_to.window(driver.driver.window_handles[-1])
            try:
                sleep(3)
                bt = (By.XPATH, '//*[@id="flat_read_more"]')
                driver.waiting_for_element(bt, 20)
                bt_ = driver.get_element(bt)
                webdriver.ActionChains(driver.driver).move_to_element(bt_).pause(1).click(bt_).perform()
                sleep(1)
                el_ = (By.XPATH, './/div[div[contains(text(), "Номер на этаже")]]/div[2]/div')
                driver.waiting_for_element(el_, 20)
                el_ = driver.get_element(el_)
                # print(el_)
                flat_ = el_.text.strip()
                # print('flat_:', flat_)
            except Exception as e:
                print('flat_ not find')
                pass
            driver.driver.close()
            driver.driver.switch_to.window(driver.driver.window_handles[-1])
            sel = '#SearchList > div > div:nth-child(1) > div > div > div > a'
            driver.waiting_for_element((By.CSS_SELECTOR, sel), 30)
            els = driver.get_elements((By.CSS_SELECTOR, sel))
            row = [park_, block_, floor_, flat_, type_, area_, price_]
            parser.add_row_info(row)

    return data
