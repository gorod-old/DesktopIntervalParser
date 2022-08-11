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
SITE_NAME = 'ЖК "Восточный"'
SITE_URL = 'http://xn--2020-z5dst.xn--p1ai/buy'
SPREADSHEET_ID = '1D3NI5Ys3eYNbbmFFBB4CNUfDV387k-R1eogdsoCjP3c'  # заказчика
SHEET_ID = 586225164  # заказчика
SHEET_NAME = 'Лист2'  # заказчика
# SPREADSHEET_ID = '1gx_dCPMI_2ygTqxcnMMY_MGnSEjcDerwaFOqPTYlbgI'  # мой
# SHEET_ID = 1343122616  # мой
# SHEET_NAME = 'Лист4'  # мой
HEADER = ['Дом', 'Этаж', 'Квартира', 'Площадь', 'Статус', 'Цена']

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
            for i in range(5):
                els = self.driver.get_elements((By.CSS_SELECTOR, '#window path'))
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
        if data_ and len(data_) > 0:
            gspread_update(data_, HEADER, SPREADSHEET_ID, SHEET_ID)  # gspread update_sheet_data()
        self.app.parser_result(self.name, len(data), time() - self.time)
        self.app.next_parser(self.name)
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
    # дома
    els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
    for house in [0, 1, 3, 4, 5]:
        if not app.run:
            return None
        # выбор дома
        webdriver.ActionChains(driver.driver).move_to_element(els[house]).click().perform()
        sleep(1)
        house_url = driver.driver.current_url
        # этажи
        els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
        parser.info_msg(f'Этажи: {len(els)}')
        rng = len(els)
        for floor in range(0, rng, 1):
            if not app.run:
                return None
            check = False
            try:
                parser.info_msg(f'Дом: {house + 1} Этаж (индекс): {floor + 1}')

                if house == 1 and 5 <= floor <= 8:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor])\
                        .move_by_offset(0, -40).click().perform()
                elif house == 0 and 6 <= floor <= 14:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor])\
                        .move_by_offset(0, -67).click().perform()
                elif house == 0 and floor == 5:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor])\
                        .move_by_offset(0, -37).click().perform()
                elif (house == 3 or house == 4 or house == 5) and 0 <= floor < 1:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                        .move_by_offset(0, -20).click().perform()
                elif (house == 3 or house == 4 or house == 5) and 1 <= floor <= 2:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                        .move_by_offset(0, -30).click().perform()
                elif (house == 3 or house == 4 or house == 5) and 16 <= floor <= 18:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                        .move_by_offset(0, 20).click().perform()
                else:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor]).click().perform()

                frame = \
                    driver.get_elements(
                        (By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp-ready '
                                          '> div > div.mfp-content > div > iframe'))[0]
                driver.driver.switch_to.frame(frame)
                check = True
            except Exception as e:
                # err_log('pars_data [Этаж клик]', str(e))
                pass

            if check:
                # Квартиры
                get_flat_info(driver, house_url, floor, house, app, parser)
                driver.driver.switch_to.default_content()
                driver.get_page(house_url)
                els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
        # break  # если парсить отдельно по домам
        driver.get_page(SITE_URL)
        sleep(1)
        els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
    return data


def get_flat_info(driver, url, floor, house, app, parser):
    els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
    hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div'))
    rng = len(els)
    for flat in range(rng):
        # print(flat)
        if not app.run:
            return
        action = webdriver.ActionChains(driver.driver)
        if house == 0:
            el, check, offset_x, offset_y = hints[flat * 2 - 2], False, 80, 80
        elif house == 1:
            el, check, offset_x, offset_y = hints[flat * 2 - 2], False, 0, 28
        else:
            el, check, offset_x, offset_y = hints[flat * 2 - 2], False, -20, 28
        for i in range(3):
            try:
                if house == 0:
                    action.move_by_offset(0, -100)
                    action.move_to_element_with_offset(els[flat], offset_x, offset_y)
                    sleep(2)
                    action.click().perform()
                else:
                    action.move_by_offset(0, -100)
                    action.move_to_element(el).move_by_offset(offset_x, offset_y)
                    action.click().perform()
                check = True
                sleep(1)
            except Exception as e:
                # err_log('pars_data [Этаж клик]', str(e))
                pass

        if check:
            house_, floor_, flat_, area_, status_, price_ = '', '', '', '', '', ''
            # Дом
            try:
                txt = driver.get_elements(
                    (By.CSS_SELECTOR,
                     'body > div > div.apartment-details > p > em:nth-child(2)'))[0].text.strip()
                house_ = txt.split(',')[-1].split('дом')[0].strip() if house == 1 else \
                    txt.split(',')[1].split('Этаж')[0].split('Дом')[1].strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [дом]', str(e))
            # Этаж
            try:
                txt = driver.get_elements(
                    (By.CSS_SELECTOR,
                     'body > div > div.apartment-details > p > em:nth-child(2)'))[0].text.strip()
                floor_ = txt.split(',')[-1].split('дом')[1].split('этаж')[0].strip() if house == 1 else \
                    txt.split(',')[1].split('Этаж')[1].split('Комнат')[0].strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [этаж]', str(e))
            # Квартира
            try:
                flat_ = driver.get_elements(
                    (By.CSS_SELECTOR, 'body > div > h1'))[0].text.split(' ')[1].split('\n')[0].strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [квартира]', str(e))
            # Площадь
            try:
                area_ = driver.get_elements(
                    (By.CSS_SELECTOR,
                     'body > div > div.apartment-details > p > strong'))[0].text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [площадь]', str(e))
            # Статус
            try:
                status_ = driver.get_elements(
                    (By.CSS_SELECTOR,
                     'body > div > div.apartment-details > div > div'))[0].text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [статус]', str(e))
            # Цена
            try:
                price_ = driver.get_elements(
                    (By.CSS_SELECTOR,
                     'body > div > div.apartment-details > span'))[0].text.strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [цена]', str(e))
            row = [house_, floor_, flat_, area_, status_, price_]
            parser.add_row_info(row, floor + 1, flat + 1)

            driver.driver.switch_to.default_content()
            driver.get_page(url)
            sleep(1)
            els = driver.get_elements((By.CSS_SELECTOR, '#window path'))

            if house == 1 and 5 <= floor <= 8:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                    .move_by_offset(0, -40).click().perform()
            elif house == 0 and 6 <= floor <= 14:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                    .move_by_offset(0, -67).click().perform()
            elif house == 0 and floor == 5:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                    .move_by_offset(0, -37).click().perform()
            elif (house == 3 or house == 4 or house == 5) and 0 <= floor < 1:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                    .move_by_offset(0, -20).click().perform()
            elif (house == 3 or house == 4 or house == 5) and 1 <= floor <= 2:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                    .move_by_offset(0, -30).click().perform()
            elif (house == 3 or house == 4 or house == 5) and 16 <= floor <= 18:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]) \
                    .move_by_offset(0, 20).click().perform()
            else:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).click().perform()

            sleep(1)
            frame = \
                driver.get_elements((By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp-ready '
                                                      '> div > div.mfp-content > div > iframe'))[0]
            driver.driver.switch_to.frame(frame)
            els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
            hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div'))

