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
SITE_URL = 'https://www.pik.ru/vladivostok'
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

    while True:
        selector = '//*[@id="__next"]/div[5]/div/div/div[2]/div/div/div[contains(@class, ' \
                   '"styles__ProjectsListItem-sc")]/a '
        driver.waiting_for_element((By.XPATH, selector), 20)
        links = driver.get_elements(
            (By.XPATH, selector))
        parser.info_msg(f'Комплексы: {len(links)}')
        urls, names = [], []
        for i, lnk in enumerate(links):
            try:
                href = lnk.get_attribute('href')
                urls.append(href)
                name = lnk.find_element(By.XPATH, './div[1]/div[1]/h2').text
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
        # selector = '#project_ChooseFlats'
        # driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
        # bt = driver.get_element((By.CSS_SELECTOR, selector))
        # try:
        #     bt.click()
        # except Exception as e:
        #     print('get flat bt click:', str(e))

        while True:
            selector = '#project_ChooseFlats'
            driver.waiting_for_element((By.CSS_SELECTOR, selector), 10)
            bt = driver.get_element((By.CSS_SELECTOR, selector))
            try:
                bt.click()
                break
            except Exception as e:
                print('get flat bt click error')
                driver.driver.refresh()

        while True:
            if not app.run:
                return None
            els = driver.get_elements((
                By.CSS_SELECTOR, '#SearchList > div > div.sc-bTUVp.bPNryZ > div > a'))
            driver.driver.execute_script("return arguments[0].scrollIntoView(true);", els[-1])
            sleep(1)
            try:
                bt = driver.get_element(
                    (By.CSS_SELECTOR,
                     '#SearchList > div > div.styles__GridFull-pm6z18-0.cqnvus > div > div > button'))
                bt.click()
                sleep(5)
            except Exception as e:
                print('more bt click:', str(e))
                break
        parser.info_msg(f'Квартиры: {len(els)}')

        driver_1 = WebDriver(headless=HEADLESS, wait_full_page_download=False)
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
                price_ = text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [Цена]', str(e))
            # № квартиры на этаже
            bt_ = None
            try:
                url = el.get_attribute('href')
                for j in range(5):
                    driver_1.get_page(url)
                    bt = (By.XPATH, '//*[@id="flat_read_more"]')
                    driver_1.waiting_for_element(bt, 20)
                    bt_ = driver_1.get_element(bt)
                    if bt_ is not None:
                        break

                # bt_.click()
                webdriver.ActionChains(driver_1.driver).move_to_element(bt_).pause(1).click(bt_).perform()
                sleep(2)
                el = (By.XPATH, './/div[div[contains(text(), "Номер на этаже")]]/div[2]/div')
                flat_ = driver_1.get_element(el).text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [№ на этаже]', str(e))

            row = [park_, block_, floor_, flat_, type_, area_, price_]
            parser.add_row_info(row)
        driver_1.close()

    return data

    # num = 0
    # els = []
    # while True:
    #     els = driver.get_elements((
    #         By.CSS_SELECTOR,
    #         '#AppWrapper > div > div > div > div.styles__Wrapper-sc-n9odu4-1.bnsRkD > '
    #         'div.styles__Results-sc-n9odu4-4.tpPsg > div > div.styles__Container-sc-1m93mro-1.jPNZOV > div > div > '
    #         'div > a'))
    #     if num == len(els):
    #         break
    #     num = len(els)
    #     driver.driver.execute_script("return arguments[0].scrollIntoView(true);", els[-1])
    #     sleep(5)
    #
    # parser.info_msg(f'Квартиры: {len(els)}')
    # driver_1 = WebDriver(headless=HEADLESS, wait_full_page_download=False)
    # for el in els:
    #     if not app.run:
    #         return None
    #     block_, section_, floor_, flat_, type_, area_, price_, status_ = '', '', '', '', '', '', '', ''
    #     # Комнат + площадь
    #     try:
    #         text = el.find_element(By.XPATH, './div[2]/p').text
    #         type_ = text.split(' ')[0].strip()
    #         area_ = text.split(' ')[1].strip() + 'м²'
    #     except Exception as e:
    #         err_log(SITE_NAME + ' get_flat_info [тип, площадь]', str(e))
    #     # Корпус + секция + этаж
    #     try:
    #         text = el.find_element(By.XPATH, './div[2]/div[1]/span').text
    #         block_ = text.split('Корпус')[1].split('·')[0].strip()
    #         section_ = text.split('секция')[1].split('·')[0].strip()
    #         floor_ = text.split('этаж')[1].strip()
    #     except Exception as e:
    #         err_log(SITE_NAME + ' get_flat_info [Корпус, секция, этаж]', str(e))
    #     # Цена
    #     try:
    #         text = el.find_element(By.XPATH, './div[3]/div/div[1]/div/div[1]/span').text
    #         price_ = text.strip()
    #     except Exception as e:
    #         err_log(SITE_NAME + ' get_flat_info [Цена]', str(e))
    #     # № квартиры на этаже
    #     bt_ = None
    #     try:
    #         url = el.get_attribute('href')
    #         for j in range(5):
    #             driver_1.get_page(url)
    #             bt = (By.XPATH, '//*[@id="InfoWrapper"]/div[1]/div/div/div/div/div[2]/div[1]/div/div[3]')
    #             driver_1.waiting_for_element(bt, 20)
    #             bt_ = driver_1.get_element(bt)
    #             if bt_ is not None:
    #                 break
    #
    #         # bt_.click()
    #         webdriver.ActionChains(driver_1.driver).move_to_element(bt_).pause(1).click(bt_).perform()
    #         sleep(2)
    #         el = (By.XPATH, './/div[div[contains(text(), "Номер на этаже")]]/div[2]/div')
    #         flat_ = driver_1.get_element(el).text.strip()
    #     except Exception as e:
    #         err_log(SITE_NAME + ' get_flat_info [№ на этаже]', str(e))
    #     try:
    #         # text = driver_1.get_element(
    #         #     (By.XPATH,
    #         #      '//*[@id="InfoWrapper"]/div[1]/div/div/div/div[1]/div[3]/div/div/div[2]')).text.strip().lower()
    #         text = driver_1.get_element(
    #             (By.XPATH,
    #              '//*[@id="InfoWrapper"]/div[1]/div/div/div/div/div[1]/div[3]/div/div/div[2]')).text.strip().lower()
    #         status_ = 'бронь' if 'забронирована' in text else ''
    #     except Exception as e:
    #         pass
    #     row = [block_, section_, floor_, flat_, type_, area_, price_, status_]
    #     parser.add_row_info(row)
    # driver_1.close()
    # return data

# новая версия сайта >>>>>>>>>>>>>>>
# from random import uniform
# from time import sleep, time
#
# from PyQt5.QtCore import QThread
# from colorama import Fore, Style
# from selenium import webdriver
# from selenium.webdriver.common.by import By
#
# from MessagePack.message import err_log
# from WebDriverPack import WebDriver
# from WebDriverPack.webDriver import try_func, timer_func
# from g_gspread import update_sheet_data as gspread_update
# from bs4 import BeautifulSoup as Bs
# import numpy as np
#
# HEADLESS = False
# SITE_NAME = 'ЖК Босфорский парк'
# SITE_URL = 'https://www.pik.ru/search/vladivostok/bosforskiypark'
# SPREADSHEET_ID = '1TfBj0p8pYFZc0RBaTbWz94xUIu8yQGNl2gGD5kY-s8M'  # заказчика
# SHEET_ID = 0  # заказчика
# SHEET_NAME = 'Лист1'  # заказчика
# # SPREADSHEET_ID = '1yBwm1qTuVjth5OoFKkK8U0FTmrKZ52ZHS1dsz3BuubA'  # мой
# # SHEET_ID = 0  # мой
# # SHEET_NAME = 'Лист1'  # мой
# HEADER = ['Корпус', 'Секция', 'Этаж', '№ на этаже', 'Тип', 'Площадь', 'Цена', 'Статус']
#
# data = []
#
#
# class SiteParser(QThread):
#     def __init__(self, app, name, stream):
#         super().__init__()
#         self.app = app
#         self.name = name
#         self.stream = stream
#         self.time = time()
#
#     def add_row_info(self, row, index_1=None, index_2=None):
#         check = np.array(row)
#         empty = True
#         for cell in row:
#             if cell != '':
#                 empty = False
#                 break
#         if len(row) == 0 or empty:
#             return
#         for r in data:
#             if np.array_equal(check, np.array(r)):
#                 return
#         index_1 = '' if index_1 is None else Fore.BLUE + f'[{index_1}]'
#         index_2 = '' if index_2 is None else Fore.BLUE + f'[{index_2}]'
#         print(Fore.YELLOW + f'[PARSER {self.stream}]', index_1, index_2, Style.RESET_ALL + f'{row}')
#         data.append(row)
#
#     def info_msg(self, msg):
#         print(Fore.YELLOW + f'[PARSER {self.stream}]', Style.RESET_ALL + str(msg))
#
#     def delete(self):
#         if self.driver:
#             print('del driver for', self.name)
#             self.driver.close()
#
#     def _create_driver(self):
#         try:
#             self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=False)
#             self.driver.get_page(SITE_URL)
#             for i in range(5):
#                 self.driver.waiting_for_element((By.CSS_SELECTOR, '#SearchList a'), 20)
#                 els = self.driver.get_elements((By.CSS_SELECTOR, '#SearchList a'))
#                 if not els or len(els) == 0:
#                     sleep(uniform(1, 5))
#                     self.driver.close()
#                     self.driver = WebDriver(headless=HEADLESS)
#                     self.driver.get_page(SITE_URL)
#                 else:
#                     break
#         except Exception as e:
#             err_log(SITE_NAME + '_create_driver', str(e))
#
#     def run(self):
#         self.info_msg(f'start parser: {self.name}')
#         self._create_driver()
#         data_ = pars_data(self)
#         count = 0 if data_ is None else len(data_)
#         if data_ and len(data_) > 0:
#             gspread_update(data_, HEADER, SPREADSHEET_ID, SHEET_ID)  # gspread update_sheet_data()
#         self.app.parser_result(self.name, count, time() - self.time)
#         self.app.next_parser(self.name, self.stream)
#         try:
#             self.driver.close()
#         except Exception as e:
#             err_log(SITE_NAME + '[SiteParser] run', str(e))
#         self.quit()
#
#
# @timer_func
# @try_func
# def pars_data(parser):
#     data.clear()
#     app = parser.app
#     driver = parser.driver
#     driver.driver.maximize_window()
#     sleep(5)
#     bt = (By.XPATH, '//*[@id="SearchList"]/div/div[2]/div/div/button')
#     while True:
#         els = driver.get_elements((By.CSS_SELECTOR, '#SearchList a'))
#         driver.driver.execute_script("return arguments[0].scrollIntoView(true);", els[-1])
#         sleep(1)
#         driver.waiting_for_element(bt, 10)
#         bt_more = driver.get_element(bt)
#         print('bt more:', bt_more)
#         if bt_more is None:
#             print('break')
#             break
#         webdriver.ActionChains(driver.driver).move_to_element(bt_more).pause(1).click(bt_more).perform()
#
#     els = driver.get_elements((By.CSS_SELECTOR, '#SearchList a'))
#     parser.info_msg(f'Квартиры: {len(els)}')
#     driver_1 = WebDriver(headless=HEADLESS, wait_full_page_download=False)
#     for i in range(0, len(els)):
#         print(i)
#         el = els[i]
#         if not app.run:
#             return None
#         block_, section_, floor_, flat_, type_, area_, price_, status_ = '', '', '', '', '', '', '', ''
#         # Комнат + площадь
#         try:
#             text = el.find_element(By.XPATH, './div[2]/div[1]/div[1]/div[1]').text
#             type_ = text.split(', ')[0].strip()
#             area_ = text.split(', ')[1].strip()
#         except Exception as e:
#             err_log(SITE_NAME + ' get_flat_info [тип, площадь]', str(e))
#         # Корпус + этаж
#         try:
#             text = el.find_element(By.XPATH, './div[2]/div[2]/div[3]/span[1]').text
#             block_ = text.split('Корпус')[1].split(', ')[0].strip()
#             floor_ = text.split('Этаж')[1].strip()
#         except Exception as e:
#             err_log(SITE_NAME + ' get_flat_info [Корпус, этаж]', str(e))
#         # № на этаже, секция, цена, статус
#         bt = (By.XPATH, '//*[@id="__next"]/div[3]/div[1]/div[2]/div/div/div/div[3]/div/button')
#         try:
#             url = el.get_attribute('href')
#             for j in range(3):
#                 driver_1.get_page(url)
#                 sleep(3)
#                 driver_1.waiting_for_element(bt, 10)
#                 bt_ = driver_1.get_element(bt)
#                 # print('bt:', bt_)
#                 if bt_ is not None:
#                     container = driver_1.get_element((
#                         By.XPATH, '//*[@id="__next"]/div[3]/div[1]/div[2]/div/div[3]/div/div[1]'))
#                     driver_1.driver.execute_script("return arguments[0].scrollIntoView(true);", container)
#                     sleep(2)
#                     webdriver.ActionChains(driver_1.driver).move_to_element(bt_).click().perform()
#                     break
#
#             sleep(1)
#             el = (By.XPATH, './/div[div[contains(text(), "Секция")]]/div[2]')
#             flat_ = driver_1.get_element(el).text.strip()
#             # print('flat:', flat_)
#             el = (By.XPATH, './/div[div[contains(text(), "Номер на этаже")]]/div[2]')
#             section_ = driver_1.get_element(el).text.strip()
#             # print('section:', section_)
#             el = (By.XPATH, '//*[@id="__next"]/div[3]/div[1]/div[2]/div/div[1]/div/div[1]/div/div[1]/div[1]')
#             price_ = driver_1.get_element(el).text.strip()
#             # print('price:', price_)
#             el = (By.XPATH, '//*[@id="__next"]/div[3]/div[1]/div[2]/div/div[2]/div[1]/div/div[1]')
#             text = driver_1.get_element(el).text.strip()
#             status_ = 'бронь' if 'забронирована' in text else ''
#             # print('status:', status_)
#         except Exception as e:
#             err_log(SITE_NAME + ' get_flat_info [№ на этаже, секция, цена, статус]', str(e))
#
#         row = [block_, section_, floor_, flat_, type_, area_, price_, status_]
#         parser.add_row_info(row)
#     driver_1.close()
#     return data
