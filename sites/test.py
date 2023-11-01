from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from MessagePack.message import err_log
from ServiceApiPack import get_proxy6_list
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
import numpy as np
from datetime import datetime, timedelta

HEADLESS = False
SITE_NAME = 'FarPost.ru'
SITE_URL = 'https://www.farpost.ru/vladivostok/realty/sell_flats/?constructionStatus[]=delivered&page=1'
# SPREADSHEET_ID = '1Bxm3997LfynLWLNpWDOsvp0LRhKg1uE_iPPSQ_aZ9Ps'  # заказчика
# SHEET_ID = 0  # заказчика
# SHEET_NAME = 'Лист1'  # заказчика
SPREADSHEET_ID = '1Bxm3997LfynLWLNpWDOsvp0LRhKg1uE_iPPSQ_aZ9Ps'  # мой
SHEET_ID = 0  # мой
SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дата', 'Тип квартиры', 'Адрес', 'Район', 'Кто', 'Площадь', 'Цена', 'Ссылка']

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
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=False, window_height=3000,
                                    proxy_api=[get_proxy6_list], proxy=True, proxy_auth=True)
            self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((By.CSS_SELECTOR, '#flats_cont > div.flats.cleaner > div.item > a'))
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
    sleep(10)

    num = 0
    all_ = 0
    while True:
        num += 1
        url = f"https://www.farpost.ru/vladivostok/realty/sell_flats/?constructionStatus[]=delivered&page={num}"
        driver.get_page(url)
        selector = f"#bulletins > div.viewport-padding-collapse > table > tbody > tr"
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
        els_ = driver.get_elements((By.CSS_SELECTOR, selector))
        if len(els_) > 0:
            els_ = els_[1:]
        all_ += len(els_)
        parser.info_msg(f'Квартиры: {len(els_)}')
        parser.info_msg(f'Всего: {all_}')
        for el in els_:
            try:
                webdriver.ActionChains(driver.driver).move_to_element(el).pause(2).click(el).perform()
                delay = uniform(1, 3)
                sleep(delay)
                row = []
                date_, type_, address_, district_, owner_, square_, price_, link_ = '', '', '', '', '', '', '', ''
                try:
                    date_ = driver.get_element((By.XPATH, '//*[@id="bulletin"]/div/header/div/div')).text.strip()
                    if "сегодня" in date_:
                        date_ = datetime.now().strftime('%d.%m.%Y')
                    elif "вчера" in date_:
                        date_ = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [date]', str(e))
                    try:
                        recap = driver.get_element(
                            (By.CSS_SELECTOR,
                             "#content h2")).text.strip()
                        print('recaptha:', recap)
                    except Exception as e:
                        recap = ''
                    if 'Вы не робот?' in recap:
                        num -= 1
                        all_ -= len(els_)
                        proxy = driver.driver.current_proxy
                        print('current proxy:', proxy)
                        driver.close()
                        driver = WebDriver(headless=HEADLESS, wait_full_page_download=False, window_height=3000,
                                           proxy_api=[get_proxy6_list], proxy=True, proxy_auth=True)
                        driver.get_page(url)
                        driver.driver.maximize_window()
                        sleep(10)
                        break
                try:
                    type_ = driver.get_element(
                        (By.XPATH, '//div[../div[contains(text(), "Вид квартиры")]]/span')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [type]', str(e))
                try:
                    address_ = driver.get_element(
                        (By.XPATH, '//div[../div[contains(text(), "Адрес")]]/span/a')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [address]', str(e))
                try:
                    district_ = driver.get_element(
                        (By.XPATH, '//div[../div[contains(text(), "Район")]]/span/a')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [district]', str(e))
                try:
                    owner_ = driver.get_element(
                        (By.XPATH, '//*[@id="fieldsetView"]/div/div[1]/div[1]/div/div[3]/span')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [owner]', str(e))
                try:
                    square_ = driver.get_element(
                        (By.XPATH, '//div[../div[contains(text(), "Площадь по документам")]]/span')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [square]', str(e))
                try:
                    price_ = driver.get_element(
                        (By.CSS_SELECTOR, 'span.viewbull-summary-price__value')).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [price]', str(e))
                link_ = driver.driver.current_url
                row.extend([date_, type_, address_, district_, owner_, square_, price_, link_])
                parser.add_row_info(row)
                driver.driver.back()
                sleep(3)
            except Exception as e:
                pass
        parser.info_msg(f'Data: {len(data)}')
        next_bt = None
        try:
            selector_ = "#bulletins > div.pager.infinite > a"
            driver.waiting_for_element((By.CSS_SELECTOR, selector_), 10)
            next_bt = driver.get_element((By.CSS_SELECTOR, selector_))
        except Exception as e:
            pass
        if next_bt is None:
            break
    return data
