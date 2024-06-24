from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
import numpy as np

HEADLESS = True
SITE_NAME = 'Kvartirogramma'
SITE_URL = 'https://realtordv.kvartirogramma.ru/'
SPREADSHEET_ID = '1TvAtKMgPRaUqhlwtfElC5ZO8-XfLvxCDGZEVlLVjvVI'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = ''  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Жилой комплекс', 'Дом', 'Секция', 'Этаж', 'Квартира', 'Тип', 'Площадь', 'Цена']

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
            self.driver = WebDriver(headless=HEADLESS, wait_full_page_download=True)
            self.driver.get_page(SITE_URL)
            # for i in range(5):
            #     els = self.driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > rect'))
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


def send_keys(driver, element: WebElement, key: str):
    action = webdriver.ActionChains(driver)
    action.send_keys_to_element(element, key).pause(uniform(.1, .5)) \
        .send_keys_to_element(element, Keys.ENTER).perform()


def sort_data(data_: list):
    sorted_, rest_ = [], []
    col1_list, col2_list = [], []
    for row in data_:
        if row[0] not in col1_list:
            col1_list.append(row[0])
        if row[1] not in col2_list:
            col2_list.append(row[1])
    print(col1_list)
    print(col2_list)
    for col1 in col1_list:
        for col2 in col2_list:
            for row in data_:
                if row[0] == col1 and row[1] == col2:
                    sorted_.append(row)
                else:
                    rest_.append(row)
            data_ = rest_.copy()
            rest_ = []
    return sorted_


@timer_func
@try_func
def pars_data(parser):
    data.clear()
    app = parser.app
    driver = parser.driver
    driver.driver.maximize_window()
    selector = '#user_login'
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    user_login = driver.get_element((By.CSS_SELECTOR, selector))
    send_keys(driver.driver, user_login, 'sales@realtordv.ru')
    selector = '#user_password'
    driver.waiting_for_element((By.CSS_SELECTOR, selector), 30)
    user_psw = driver.get_element((By.CSS_SELECTOR, selector))
    send_keys(driver.driver, user_psw, 'realtorsales1221')
    sleep(3)
    selector = 'a.m-estate-card'
    els = driver.get_elements((By.CSS_SELECTOR, selector))
    print(f"комплексы: {len(els)}")
    for i in range(len(els)):
        if not app.run:
            return None
        webdriver.ActionChains(driver.driver).move_to_element(els[i]).click().perform()
        sleep(3)
        complex_, house_ = '', ''
        try:
            selector = 'body > div > div.site__content > header > div.m-header__head > div.m-header__title > h1'
            complex_ = driver.get_element((By.CSS_SELECTOR, selector)).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [complex_]', str(e))

        while True:
            if not app.run:
                return None
            selector = '#flats-list > div.m-flats-block'
            houses = driver.get_elements((By.CSS_SELECTOR, selector))
            print(f"дома: {len(houses)}")
            for h in houses:
                if not app.run:
                    return None
                try:
                    xpath = './div[1]/div/div[2]/a'
                    house_ = h.find_element(By.XPATH, xpath).text.lower().split('дом')[1].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [house_]', str(e))

                xpath = './div[2]/div/div'
                flats = h.find_elements(By.XPATH, xpath)
                print(f"квартиры: {len(flats)}")
                for flat in flats:
                    if not app.run:
                        return None
                    complex_, house_, section_, floor_, flat_, type_, area_, price_ = \
                        complex_, house_, '', '', '', '', '', ''
                    check = ""
                    try:
                        check = flat.find_element(
                            By.CSS_SELECTOR,
                            'div.m-flat-item__flat > a > span.m-flat-item__flat-type').text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [check]', str(e))
                    if "Парковка" not in check:
                        try:
                            flat_ = flat.find_element(
                                By.CSS_SELECTOR,
                                'div.m-flat-item__flat > a > span.m-flat-item__flat-number').text.strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                        try:
                            section_ = flat.find_element(
                                By.CSS_SELECTOR,
                                'div.m-flat-item__flat > a > span.m-flat-item__flat-entrance').text.strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [section_]', str(e))
                        try:
                            floor_ = flat.find_element(
                                By.CSS_SELECTOR,
                                'div.m-flat-item__flat > a > span.m-flat-item__flat-floor').text.strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [floor_]', str(e))
                        try:
                            type_ = flat.find_element(
                                By.CSS_SELECTOR,
                                'div.m-flat-item__flat > a > span.m-flat-item__flat-rooms').text.strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [type_]', str(e))
                        try:
                            area_ = flat.find_element(
                                By.CSS_SELECTOR,
                                'div.m-flat-item__flat > a > span.m-flat-item__flat-area').text.split(' ')[0].strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [area_]', str(e))
                        try:
                            price_ = flat.find_element(
                                By.CSS_SELECTOR,
                                'div.m-flat-item__flat > a > span.m-flat-item__flat-price').text.strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [price_]', str(e))
                        row = [complex_, house_, section_, floor_, flat_, type_, area_, price_]
                        parser.add_row_info(row)
                    else:
                        print("not flat")

            try:
                xpath = '/html/body/div/div[2]/div[3]/div[2]/nav/ul/li/a[contains(text(),"Следующая ›")]'
                next_bt = driver.get_element((By.XPATH, xpath))
                next_bt.click()
                sleep(1)
            except Exception as e:
                print('next bt not find')
                break

        driver.get_page(SITE_URL)
        selector = 'a.m-estate-card'
        els = driver.get_elements((By.CSS_SELECTOR, selector))
        sleep(5)

        # selector = 'body > div.site > div.site__content > div.m-cubes-canvas.m-cubes-canvas--default > div > div > ' \
        #            'div > div.m-cubes-building__entrances > div > div > div.m-cubes-entrance__floors > ' \
        #            'div > div.m-cubes-floor__cubes > a '
        # # driver.waiting_for_elements((By.CSS_SELECTOR, selector), 10)
        # flats = driver.get_elements((By.CSS_SELECTOR, selector))
        # print(f"квартиры: {len(flats)}")
        # for flat in flats:
        #     if not app.run:
        #         return None
        #     # i += 1
        #     # if i == 11:
        #     #     break
        #     webdriver.ActionChains(driver.driver).move_to_element(flat).click(flat).perform()
        #     sleep(1)
        #     complex_, house_, section_, floor_, flat_, type_, area_, price_ = complex_, '', '', '', '', '', '', ''
        #     check = ""
        #     try:
        #         els_ = driver.get_elements(
        #             (By.CSS_SELECTOR,
        #              "div.modal.fade.show > div > div > div.modal-body > div:nth-child(1) "
        #              "> div.col-sm-10 > span > a"))
        #         house_ = els_[0].text.strip()
        #         flat_ = els_[1].text.strip().split(' ')[-1]
        #         check = els_[1].text.strip()
        #     except Exception as e:
        #         err_log(SITE_NAME + ' pars_data [house_, flat_]', str(e))
        #     if "Парковка" not in check:
        #         try:
        #             text = driver.get_element(
        #                 (By.CSS_SELECTOR, "div.modal.fade.show > div > div > div.modal-body > div:nth-child(3) > "
        #                                   "div.col-sm-8 > p")).text.strip()
        #             section_ = text.split(', ')[0]
        #             floor_ = text.split(', ')[1]
        #         except Exception as e:
        #             err_log(SITE_NAME + ' pars_data [section_, floor_]', str(e))
        #         try:
        #             text = driver.get_element(
        #                 (By.CSS_SELECTOR, "div.modal.fade.show > div > div > div.modal-body > div:nth-child(3) > "
        #                                   "div.col-sm-8 > div.h2")).text.strip()
        #             area_ = text.split('  ')[1].split('м²')[0].strip()
        #             type_ = text.split('  ')[0].strip()
        #         except Exception as e:
        #             err_log(SITE_NAME + ' pars_data [area_, type_]', str(e))
        #         try:
        #             price_ = driver.get_element(
        #                 (By.CSS_SELECTOR, "div.modal.fade.show > div > div > div.modal-body > div:nth-child(3) > "
        #                                   "div.col-sm-8 > div.h1 > strong")).text.strip()
        #         except Exception as e:
        #             err_log(SITE_NAME + ' pars_data [price_]', str(e))
        #         row = [complex_, house_, section_, floor_, flat_, type_, area_, price_]
        #         parser.add_row_info(row)
        #     else:
        #         print("not flat")
        #     sel = 'div.modal.fade.show > div > div > div.modal-footer.clearfix > button'
        #     close = driver.get_element((By.CSS_SELECTOR, sel))
        #     webdriver.ActionChains(driver.driver).move_to_element(close).click().perform()
        # driver.driver.back()
        # selector = 'a.m-estate-card'
        # els = driver.get_elements((By.CSS_SELECTOR, selector))
        # sleep(5)
    return sort_data(data)
