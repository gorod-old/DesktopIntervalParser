from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from WinSoundPack import beep
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Исторический'
# SITE_URL = 'https://xn--e1aceabgfd3aujei7e.xn--p1ai/'
SITE_URL = 'https://xn--e1aceabgfd3aujei7e.xn--p1ai/#/profitbase/projects/houses?filter=property.status:AVAILABLE'
SPREADSHEET_ID = '1ZZxQ_G1BYZ08LkzCWnF4T7hVgA4T-Utt30oaP_cRgOU'  # заказчика
SHEET_ID = 603957158  # заказчика
SHEET_NAME = 'Лист2'  # заказчика
# SPREADSHEET_ID = '1uHEuC0_rn6gGjmD3O4QEfsdDVfVKidG0hPVFU7sHPn4'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', '№ квартиры', 'Тип', 'Площадь', 'Цена']

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

    els = []
    try:
        sleep(15)
        driver.waiting_for_element((By.CSS_SELECTOR, '#profitbase_front_widget'), 20)
        iframe = driver.get_element((By.CSS_SELECTOR, '#profitbase_front_widget'))
        driver.driver.switch_to.frame(iframe)
        selector = 'body > app-root > app-catalog > app-stock > div > main > app-projects > div.stock__content > ' \
                   'app-house-cards > section > div > app-house-card > div > a '
        driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
        els = driver.get_elements((By.CSS_SELECTOR, selector))
    except Exception as e:
        print(str(e))
    print('els:', len(els))
    for i in range(len(els)):
        if not app.run:
            return None
        try:
            webdriver.ActionChains(driver.driver).click(els[i]).perform()
            selector_ = 'body > app-root > app-catalog > app-stock > div > main > app-house > ' \
                        'div.stock__panel.ng-star-inserted > app-tabs > app-desktop-tabs > section > p-tabmenu > div ' \
                        '> ul > li:nth-child(4) > a '
            driver.waiting_for_element((By.CSS_SELECTOR, selector_), 20)
            bt_to_floors = driver.get_element((By.CSS_SELECTOR, selector_))
            webdriver.ActionChains(driver.driver).move_to_element(bt_to_floors).pause(3).click().perform()
            # этажи
            while True:
                if not app.run:
                    return None
                sleep(5)
                selector_ = 'tr.ng-star-inserted'
                driver.waiting_for_element((By.CSS_SELECTOR, selector_), 20)
                flats = driver.get_elements((By.CSS_SELECTOR, selector_))
                print('flats:', len(flats))
                for f in flats:
                    if not app.run:
                        return None
                    house_, floor_, flat_, type_, area_, price_ = '', '', '', '', '', ''
                    try:
                        house_ = f.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [house_]', str(e))
                    try:
                        floor_ = f.find_element(By.CSS_SELECTOR, "td:nth-child(10)").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [floor_]', str(e))
                    try:
                        flat_ = f.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [flat_]', str(e))
                    try:
                        type_ = f.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [type_]', str(e))
                    try:
                        area_ = f.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip() + " м2"
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [area_]', str(e))
                    try:
                        price_ = f.find_element(By.CSS_SELECTOR, "td:nth-child(7) > app-property-price").text.strip()
                    except Exception as e:
                        err_log(SITE_NAME + ' pars_data [price_]', str(e))
                    row = [house_, floor_, flat_, type_, area_, price_]
                    parser.add_row_info(row)

                selector_ = 'body > app-root > app-catalog > app-stock > div > main > app-house > ' \
                            'div.stock__content.ng-star-inserted > app-properties-table > ' \
                            'app-desktop-properties-table > div > div.desktop-properties__paginator > p-paginator > ' \
                            'div > button.p-ripple.p-element.p-paginator-next.p-paginator-element.p-link '
                bt_next = driver.get_element((By.CSS_SELECTOR, selector_))
                if bt_next and bt_next.is_enabled():
                    bt_next.click()
                else:
                    print('next disabled - break')
                    break

            btn_home = driver.get_element((By.CSS_SELECTOR, '#navigation-home'))
            print('bt_home:', btn_home)
            webdriver.ActionChains(driver.driver).move_to_element(btn_home).pause(5).click(btn_home).perform()
            sleep(5)
            selector = 'body > app-root > app-catalog > app-stock > div > main > app-projects > div.stock__content > ' \
                       'app-house-cards > section > div > app-house-card > div > a '
            driver.waiting_for_element((By.CSS_SELECTOR, selector), 20)
            els = driver.get_elements((By.CSS_SELECTOR, selector))
        except Exception as e:
            print(str(e))

    return data

