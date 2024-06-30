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
SITE_NAME = 'Золотая долина'
SITE_URL = 'http://золотая-долина25.рф/vybrat-kvartiru-2'
SPREADSHEET_ID = '1l36TjgHYQUOC3Xn9Y4meqMzc0-y7bBQj3sHUx2FXyE0'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '13XINVPnlGCM_ewe49tyXtbpEF8Ye-ZPWZFtvItKI4Z8'  # мой
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
            self.driver = WebDriver(headless=HEADLESS)
            self.driver.get_page(SITE_URL)
            for i in range(5):
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
    els = driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > path'))
    parser.info_msg(f'Этажи: {len(els)}')
    rng = len(els)
    d, f = '', ''

    # обманываем всплывающее окно
    try:
        webdriver.ActionChains(driver.driver).move_to_element(els[0]).move_by_offset(0, 10).click().perform()
        frame = driver.get_elements((By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp'
                                                      '-ready > div > div.mfp-content > div > iframe'))[0]
        driver.driver.switch_to.frame(frame)
        el = driver.get_element((By.CSS_SELECTOR, '#blockquote > h2')).text
        d = int(el.split('дом')[0].strip()) if 'дом' in el else 1
        f = int(el.split('Этаж')[1].strip())
        parser.info_msg(f'Дом: {d}, Этаж: {f}, Индекс: 0')
        get_flat_info(driver, f, d, 0, app, parser)
        driver.driver.switch_to.default_content()
        driver.get_page(SITE_URL)
        sleep(1)
        els = driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > path'))
    except Exception as e:
        pass

    for floor in range(0, rng, 1):
        if not app.run:
            return None
        check = False

        try:
            if 0 <= floor <= 8 or 19 <= floor <= 25 or floor == 38:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, 10).click().perform()
            elif floor == 9 or floor == 26:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -30).click().perform()
            elif 10 <= floor <= 18 or floor == 39 or 27 <= floor <= 37 or 41 <= floor <= 42:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -10).click().perform()
            sleep(1)
            frame = driver.get_elements((By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp'
                                                          '-ready > div > div.mfp-content > div > iframe'))[0]
            driver.driver.switch_to.frame(frame)
            el = driver.get_element((By.CSS_SELECTOR, '#blockquote > h2')).text
            d = int(el.split('дом')[0].strip()) if 'дом' in el else 1
            f = int(el.split('Этаж')[1].strip())
            parser.info_msg(f'Дом: {d}, Этаж: {f}, Индекс: {floor}')
            check = True
        except Exception as e:
            # err_log('pars_data [Этаж клик]', str(e))
            pass
        if check:
            # Квартиры
            get_flat_info(driver, f, d, floor, app, parser)
            driver.driver.switch_to.default_content()
            driver.get_page(SITE_URL)
            sleep(1)
            els = driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > path'))
        # break
    return data


def get_flat_info(driver, f, d, floor, app, parser):
    hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div > div.flag-text'))
    els = driver.get_elements((By.CSS_SELECTOR, '#scroller > svg > path'))
    rng = len(hints)/2
    parser.info_msg(f'Квартиры: {int(rng)}')

    index_list = []
    for i in range(0, len(hints), 2):
        if els[i // 2].get_attribute('fill') == '#3ba108':
            index_list.append(i)
    parser.info_msg(f'Свободных: {len(index_list)}')

    for i, index in enumerate(index_list):
        if not app.run:
            return

        check = False
        html = None
        offset_x, offset_y = 0, 32
        for j in range(2):
            try:
                action = webdriver.ActionChains(driver.driver)
                action.move_by_offset(100, 100).perform()
                action.move_to_element(hints[index]).move_by_offset(offset_x, offset_y).click().perform()
                action.reset_actions()
                sleep(2)
                html = driver.driver.page_source
                soup = Bs(html, 'html.parser')
                check = soup.select('body > div.apartment-info-box > h1')[0]
                if check:
                    break
            except Exception as e:
                offset_x -= 90
                offset_y -= 100
                # err_log('get_flat_info [action]', str(e))
                pass
        row = [d, f]
        if check:
            flat_, area_, price_ = '', '', ''
            soup = Bs(html, 'html.parser')
            # Номер квартиры
            try:
                txt = soup.select('body > div.apartment-info-box > h1')[0].getText()
                flat_ = int(txt.split('Квартира №')[1].split(' ')[0].strip())
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [квартира]', str(e))
            # Площадь
            try:
                area_ = soup.select('body > div.apartment-info-box > div.apartment-details > p > strong')[0] \
                    .getText().strip()
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [площадь]', str(e))
            # Цена
            try:
                price_ = soup.select('body > div.apartment-info-box > div.apartment-details > span')[0] \
                    .getText(strip=True)
            except Exception as e:
                err_log(SITE_NAME + ' get_flat_info [цена]', str(e))
            row.extend([flat_, area_, price_])
            parser.add_row_info(row, floor, flat_)

            if i < len(index_list) - 1:
                driver.driver.back()
                sleep(2)
                frame = driver.get_elements((By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp'
                                                              '-ready > div > div.mfp-content > div > iframe'))[0]
                driver.driver.switch_to.frame(frame)
                hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div > div.flag-text'))

