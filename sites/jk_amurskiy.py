from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from MessagePack.message import err_log, print_exception_msg
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Амурский'
SITE_URL = 'https://xn--80atmq1a.xn--p1ai/vybrat-kvartiru'
SPREADSHEET_ID = '11_f51G2keBZMotd-G6VNE1de4q0sGzsyb3d6HBXFbwM'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1-kg2EIWS6XYx0TQ5G5OLpaIYQ0xu3dA8UA1g_bddDXw'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Секция', 'Этаж', '№ квартиры', 'Площадь', 'Комнат', 'Цена']

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
            self.driver.get_page(SITE_URL, )
            for i in range(5):
                sleep(3)
                self.driver.waiting_for_element((By.CSS_SELECTOR, '#scroller > svg > path'), 20)
                els = self.driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > path'))
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
    for i in range(5, 15, 1):
        if not app.run:
            return None
        url = f"https://xn--80atmq1a.xn--p1ai/component/megaplan/?view=megaplan&id={i}"
        driver.get_page(url)
        sleep(1)
        section_ = ""
        try:
            section_ = driver.get_element((By.CSS_SELECTOR, '#blockquote > h2')).text.strip()
            parser.info_msg(f"секция: {section_}")
        except Exception as e:
            print(str(e))

        els = get_floors(driver)
        parser.info_msg(f"этажи: {len(els)}")
        for k in range(len(els)):
            # k = 9
            # print(k)
            if not app.run:
                return None
            el = els[k]
            status_, floor_, hints, urls = '', '', [], []
            try:
                if k < 18:
                    webdriver.ActionChains(driver.driver).move_to_element(el).pause(1).click(el).perform()
                else:
                    webdriver.ActionChains(driver.driver).move_to_element(el)\
                        .move_by_offset(0, -5).pause(1).click().perform()
                sleep(2)
                frame = driver.get_elements(
                    (By.CSS_SELECTOR,
                     'div.mfp-content > div > iframe'))[0]
                driver.driver.switch_to.frame(frame)
                floor_ = driver.get_element((By.CSS_SELECTOR, '#blockquote > h2')).text.strip()
                parser.info_msg(f"этаж: {floor_}")
                # hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div'))
                hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > a.xx_etaj.iframe'))
                for h in hints:
                    url_ = h.get_attribute('href')
                    urls.append(url_)
            except Exception as e:
                # print(str(e))
                pass
            if len(hints) > 0:
                parser.info_msg(f"квартиры: {len(hints)}")
                driver.driver.switch_to.default_content()
                driver.driver.execute_script("window.open('');")
                driver.driver.switch_to.window(driver.driver.window_handles[1])
                for u in urls:
                    if not app.run:
                        return None
                    driver.get_page(u)
                    sleep(1)
                    try:
                        status_ = driver.get_element(
                            (By.CSS_SELECTOR,
                             'body > div.apartment-info-box > div.apartment-details > div > div.status')).text.strip()
                    except Exception as e:
                        # err_log(SITE_NAME + ' pars_data [status_]', str(e))
                        pass

                    if 'в продаже' in status_:
                        flat_, area_, rooms_, price_ = '', '', '', ''
                        try:
                            flat_ = driver.get_element((By.CSS_SELECTOR, 'body > div.apartment-info-box > h1')).text
                            if '№' in flat_:
                                flat_ = flat_.split('№')[1]
                            flat_ = flat_.split('\n')[0].strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [flat_]', str(e))

                        try:
                            area_ = driver.get_element(
                                (By.CSS_SELECTOR,
                                 'body > div.apartment-info-box > div.apartment-details > p > strong')).text.strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [area_]', str(e))

                        try:
                            rooms_ = driver.get_element(
                                (By.CSS_SELECTOR,
                                 'body > div.apartment-info-box > div.apartment-details > p > em:nth-child(3)')) \
                                .text.strip().split(' ')[1]
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [rooms_]', str(e))

                        try:
                            price_ = driver.get_element(
                                (By.CSS_SELECTOR,
                                 'body > div.apartment-info-box > div.apartment-details > span')).text.strip()
                        except Exception as e:
                            err_log(SITE_NAME + ' pars_data [price_]', str(e))

                        row = [section_, floor_, flat_, area_, rooms_, price_]
                        parser.add_row_info(row)

                driver.driver.close()
                driver.driver.switch_to.window(driver.driver.window_handles[0])

            driver.driver.switch_to.default_content()
            close = driver.get_element((By.CSS_SELECTOR, 'button.mfp-close'))
            if close:
                close.click()
            else:
                driver.driver.back()
                els = get_floors(driver)

    return data


def get_floors(driver):
    els = []
    try:
        zoom_minus = driver.get_element((By.CSS_SELECTOR, '#zoom_minus'))
        if zoom_minus:
            for i in range(12):
                zoom_minus.click()
                sleep(.2)
        els = driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > path, #scroller > svg > rect'))
    except Exception as e:
        # print(str(e))
        pass
    return els
