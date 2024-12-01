from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Квартал Чехова'
SITE_URL = 'https://city-complex.ru/catalog?project=kvartal-chekhova&sorting=cheap'
SPREADSHEET_ID = '1npzmKt_So9RcCBLpG5UvIBwsxTw0o_1ajjUJfl3I0kQ'  # заказчика
SHEET_ID = 1876162083  # заказчика
SHEET_NAME = 'parser'  # заказчика
# SPREADSHEET_ID = ''  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Секция', 'Этаж', '№ квартиры', 'Тип', 'Площадь', 'Цена', 'Статус']

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
            # for i in range(5):
            #     els = self.driver.get_elements(
            #         (By.CSS_SELECTOR, '#__next'))
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
    sleep(5)
    while True:
        selector = 'a._1m98od20'
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
        els = driver.get_elements((By.CSS_SELECTOR, selector))

        try:
            bt_more = driver.get_element((By.XPATH, "//*[contains(text(),'Показать еще')]"))
            webdriver.ActionChains(driver.driver).move_to_element(bt_more).pause(2).click(bt_more).perform()
            sleep(1)
        except Exception as e:
            print('exit')
            break
    print(len(els))

    for el in els:
        url = el.get_attribute('href')
        print(url)
        section_, floor_, flat_, type_, area_, price_, status_ = '', '', '', '', '', '', ''
        try:
            xpath = ".//*[contains(text(),'Переуступка')]"
            status_ = el.find_element(By.XPATH, xpath).text.strip().lower()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [status_]', str(e))
        if status_ == '':
            try:
                xpath = ".//*[contains(text(),'переуступка')]"
                status_ = el.find_element(By.XPATH, xpath).text.strip().lower()
            except Exception as e:
                # err_log(SITE_NAME + ' pars_data [status_]', str(e))
                pass
        try:
            xpath = "./div[3]/div[2]/div[1]"
            type_ = el.find_element(By.XPATH, xpath).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [type_]', str(e))
        driver.driver.execute_script("window.open('');")
        driver.driver.switch_to.window(driver.driver.window_handles[1])
        driver.get_page(url)
        sleep(2)
        try:
            xpath = "//h1"
            text = driver.driver.find_element(By.XPATH, xpath).text.strip()
            flat_ = text.split('№')[1].split('-')[0].strip()
            area_ = text.split('-')[1].strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [flat_, area_]', str(e))
        try:
            xpath = "//*[@id='__next']/div/main/section/div/div[2]/div[2]/div[1]/div[2]/div[2]/div[2]"
            floor_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [floor_]', str(e))
        try:
            xpath = "//*[@id='__next']/div/main/section/div/div[2]/div[2]/div[1]/div[2]/div[3]/div[2]"
            section_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [section_]', str(e))
        try:
            xpath = "//*[@id='__next']/div/main/section/div/div[2]/div[2]/div[1]/div[3]"
            price_ = driver.driver.find_element(By.XPATH, xpath).text.strip()
        except Exception as e:
            err_log(SITE_NAME + ' pars_data [price__]', str(e))

        row = [section_, floor_, flat_, type_, area_, price_, status_]
        parser.add_row_info(row)
        driver.driver.close()
        driver.driver.switch_to.window(driver.driver.window_handles[0])
        sleep(2)

    return data
