from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Босфорский парк'
SITE_URL = 'https://www.pik.ru/vladivostok/projects'
SPREADSHEET_ID = '1TfBj0p8pYFZc0RBaTbWz94xUIu8yQGNl2gGD5kY-s8M'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1yBwm1qTuVjth5OoFKkK8U0FTmrKZ52ZHS1dsz3BuubA'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Комплекс', 'Блок', 'Этаж', 'Секция', '№ на этаже', 'Тип', 'Площадь', 'Цена', 'Url']

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

    urls_ = {}
    for i, url in enumerate(urls):
        if not app.run:
            return None
        driver.get_page(url)

        while True:
            selector = '#uxs_93ncf79agaaqqt8narsz5lua_form > form'
            driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
            check = driver.get_element((By.CSS_SELECTOR, selector))
            if check:
                driver.driver.refresh()
            else:
                break

        while True:
            if not app.run:
                return None
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
        flat_urls = []
        for el in els:
            if not app.run:
                return None
            flat_url = el.get_attribute('href')
            flat_urls.append(flat_url)
        parser.info_msg(f'Квартиры: {len(flat_urls)}')
        urls_[names[i]] = flat_urls
        driver.driver.close()
        driver.driver.switch_to.window(driver.driver.window_handles[0])

    for key, flat_urls in urls_.items():
        print(key)
        for flat_url in flat_urls:
            if not app.run:
                return None
            driver.driver.execute_script("window.open('');")
            driver.driver.switch_to.window(driver.driver.window_handles[-1])
            driver.get_page(flat_url)
            sleep(1)
            # Бронь
            lock = None
            try:
                el_ = (By.XPATH, '//div[contains(text(),"Квартира забронирована")]')
                lock = driver.get_element(el_)
                print(lock.text.strip())
            except Exception as e:
                # err_log(SITE_NAME + ' get_flat_info [Бронь]', str(e))
                pass
            if not lock:
                park_, block_, floor_, section_, flat_, type_, area_, price_, url_ = key, '', '', '', '', '', '', '', flat_url
                # Комнат + площадь
                try:
                    el_ = (By.XPATH, '//*[@id="__next"]/div[3]/div[1]/div[2]/div/div[1]/div/h1')
                    driver.waiting_for_element(el_, 20)
                    text = driver.get_element(el_).text.strip()
                    type_ = text.split(' ')[0].strip()
                    area_ = text.split(f'{type_}')[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [Комнат + площадь]', str(e))
                # Цена
                try:
                    el_ = (By.XPATH, '//*[@id="__next"]/div[3]/div[1]/div[2]/div/div[1]/div/div[1]/div/div[1]/div[1]')
                    driver.waiting_for_element(el_, 20)
                    price_ = driver.get_element(el_).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [Цена]', str(e))
                try:
                    bt = (By.XPATH, '//*[@id="flat_read_more"]')
                    driver.waiting_for_element(bt, 20)
                    bt_ = driver.get_element(bt)
                    webdriver.ActionChains(driver.driver).move_to_element(bt_).pause(1).click(bt_).perform()
                    sleep(1)
                    el_ = (By.XPATH, '//div[contains(text(),"Номер на этаже")]/following-sibling::div')
                    driver.waiting_for_element(el_, 20)
                    el_ = driver.get_element(el_)
                    flat_ = el_.text.strip()
                except Exception as e:
                    print('flat_ not find')
                    print(flat_url)
                    print(str(e))
                    pass
                # Корпус
                try:
                    el_ = (By.XPATH, '//div[contains(text(),"Корпус")]/following-sibling::div')
                    driver.waiting_for_element(el_, 20)
                    block_ = driver.get_element(el_).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [Корпус]', str(e))
                # Этаж
                try:
                    el_ = (By.XPATH, '//div[contains(text(),"Этаж")]/following-sibling::div')
                    driver.waiting_for_element(el_, 20)
                    floor_ = driver.get_element(el_).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [Этаж]', str(e))
                # Секция
                try:
                    el_ = (By.XPATH, '//div[contains(text(),"Секция")]/following-sibling::div')
                    driver.waiting_for_element(el_, 20)
                    section_ = driver.get_element(el_).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [Секция]', str(e))
                row = [park_, block_, floor_, section_, flat_, type_, area_, price_, url_]
                # parser.add_row_info(row)
                print(row)
                data.append(row)
            else:
                print('flat is locked')
            driver.driver.close()
            driver.driver.switch_to.window(driver.driver.window_handles[-1])

    return data
