from random import uniform, choice
from time import sleep, time

import requests
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

HEADLESS = False
SITE_NAME = 'ЖК "Нагорный'
SITE_URL = 'https://vladivostok.domclick.ru/complexes/zhk-nagornyi__115784?utm_referrer=https%3A%2F%2Fwww.google.com%2F'
SPREADSHEET_ID = '1nnBCs9SBAg-5xlFmWPaNWaBDGL87AM0ADp-kVLAFWqg'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1tP8k_sPupI240GmoXYw1IiMvY4vXGC8z-Yt6FaPva4M'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', 'Квартира', 'Площадь', 'Цена']

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
            # for i in range(5):
            #     els = self.driver.get_elements((By.CSS_SELECTOR, 'sc_pagination_button'))
            #     if not els or len(els) == 0:
            #         sleep(uniform(1, 5))
            #         self.driver.close()
            #         self.driver = WebDriver(headless=HEADLESS)
            #         self.driver.get_page(SITE_URL)
            #     else:
            #         break

            # self.driver = None
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
    # data.clear()
    # app = parser.app
    # driver = parser.driver
    # # driver.driver.maximize_window()
    # pag_bts = driver.get_elements((By.CSS_SELECTOR, 'sc_pagination_button'))
    # parser.info_msg(f'Страниц: {len(pag_bts)}')
    # for bt in pag_bts:
    #     bt.click()
    sleep(100)

    # ua_list = get_user_agents_list()
    # user_agent = {
    #     'user-agent': choice(ua_list),
    #     'accept': '*/*'
    # }
    # r = request_data(SITE_URL, user_agent, None)
    #
    # print(r.text)


def request_data(url, headers=None, proxies=None, params=None):
    r = requests.get(url, headers=headers, proxies=proxies, params=params)
    return r


def get_user_agents_list():
    ua_list = open('text_files/user-agents.txt').read().strip().split('\n')
    for ua in ua_list:
        if len(ua) == 0:
            ua_list.remove(ua)
    return ua_list
