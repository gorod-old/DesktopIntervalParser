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
SITE_NAME = 'жкаякс.рф'
SITE_URL = 'http://xn--80almb9a8e.xn--p1ai/buy'
SPREADSHEET_ID = '1Rwh-Iu7BWWUUZsysHqG2k-Tmm8-K78QtgFXNW_WBQ-w'  # заказчика
SHEET_ID = 213579104  # заказчика
SHEET_NAME = 'Лист2'  # заказчика
# SPREADSHEET_ID = '1gx_dCPMI_2ygTqxcnMMY_MGnSEjcDerwaFOqPTYlbgI'  # мой
# SHEET_ID = 1158185577  # мой
# SHEET_NAME = 'Лист3'  # мой
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

    def run(self):
        self.info_msg(f'start parser: {self.name}')
        self._create_driver()
        data_ = pars_data(self)
        if data_ and len(data_) > 0:
            gspread_update(data_, HEADER, SPREADSHEET_ID, SHEET_ID)  # gspread update_sheet_data()
        self.app.parser_result(self.name, len(data), time() - self.time)
        self.app.next_parser(self.name)
        self.driver.close()
        self.quit()


@timer_func
@try_func
def pars_data(parser):
    data.clear()
    app = parser.app
    driver = parser.driver
    driver.driver.maximize_window()
    els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
    parser.info_msg(f'Этажи: {len(els)}')
    rng = len(els)
    for floor in range(1, rng, 1):
        if not app.run:
            return None
        check = False
        try:
            if 14 <= floor <= 21:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -20).click().perform()
            elif 22 <= floor <= 23:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -40).click().perform()
            elif floor == 33:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).click().perform()
            elif 35 <= floor <= 47:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -5).click().perform()
            else:
                webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, 10).click().perform()
            frame = driver.get_elements((By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp'
                                                          '-ready > div > div.mfp-content > div > iframe'))[0]
            driver.driver.switch_to.frame(frame)
            el = driver.get_element((By.CSS_SELECTOR, '#blockquote > h2')).text
            d = int(el.split('Этаж ')[0].split('Дом ')[1].strip())
            f = int(el.split('Этаж ')[1].strip())
            parser.info_msg(f'Дом: {d} Этаж (индекс): {floor + 1}')
            check = True
        except Exception as e:
            # err_log('pars_data [Этаж клик]', str(e))
            pass
        if check:
            # Квартиры
            get_flat_info(driver, floor, app, parser)
            driver.driver.switch_to.default_content()
            driver.get_page(SITE_URL)
            sleep(1)
            els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
    return data


def get_flat_info(driver, floor, app, parser):
    hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div'))
    rng = len(hints)/2
    parser.info_msg(f'Квартиры: {int(rng)}')
    flat = 0
    html = None
    repeat = 0
    while flat < rng:
        if not app.run:
            return
        index = (flat + 1) * 2 - 2
        hint = hints[index]
        check = False
        offset_x = 0
        offset_y = 40
        img = driver.get_element((By.CSS_SELECTOR, '#scroller > svg > image'))
        action = webdriver.ActionChains(driver.driver)
        for i in range(2):
            try:
                action.move_to_element(img)
                if flat == 0 or flat == 9:
                    sleep(.5)
                    driver.driver.execute_script("arguments[0].scrollIntoView();", img)
                    sleep(1)
                action.move_to_element(hint).move_by_offset(offset_x, offset_y).click().perform()
                # action.move_by_offset(offset_x, offset_y).click().perform()
                action.reset_actions()
                html = driver.driver.page_source
                check = True
                sleep(1)
            except Exception as e:
                # err_log('get_flat_info [action]', str(e))
                offset_x += 20
                offset_y += 20
                pass
        row = []
        if check:
            house_, floor_, flat_, area_, status_, price_ = '', '', '', '', '', ''
            soup = Bs(html, 'html.parser')
            # Дом + Номер квартиры
            try:
                txt = soup.select('body > div.apartment-info-box > h1')[0].getText()
                house_ = txt.split('Квартира ')[0].split('Дом ')[1].strip()
                flat_ = txt.split('Квартира ')[1].split(' ')[0].strip()
            except Exception as e:
                err_log('get_flat_info [дом]', str(e))
            # Этаж
            try:
                txt = soup.select(
                    'body > div.apartment-info-box > div.apartment-details > p > em:nth-child(2)')[0].getText()
                floor_ = txt.split('Этаж ')[1].strip()
            except Exception as e:
                err_log('get_flat_info [этаж]', str(e))
            # Площыдь
            try:
                area_ = soup.select('body > div.apartment-info-box > div.apartment-details > p > strong')[0] \
                    .getText().strip()
            except Exception as e:
                err_log('get_flat_info [площадь]', str(e))
            # Статус
            try:
                status_ = soup.select(
                    'body > div.apartment-info-box > div.apartment-details > div.status_kom > div')[0] \
                    .getText(strip=True)
            except Exception as e:
                err_log('get_flat_info [статус]', str(e))
            # Цена
            try:
                price_ = soup.select('body > div.apartment-info-box > div.apartment-details > div.pr > span')[0] \
                    .getText(strip=True)
            except Exception as e:
                err_log('get_flat_info [цена]', str(e))
            row = [house_, floor_, flat_, area_, status_, price_]
        if (len(row) == 0 or '' in row) and repeat < 3:
            repeat += 1
        else:
            parser.add_row_info(row, floor + 1, flat + 1)
            repeat = 0
            flat += 1

        driver.driver.switch_to.default_content()
        driver.get_page(SITE_URL)
        sleep(1)
        els = driver.get_elements((By.CSS_SELECTOR, '#window path'))
        if 14 <= floor <= 21:
            webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -20).click().perform()
        elif 22 <= floor <= 23:
            webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -40).click().perform()
        elif floor == 33:
            webdriver.ActionChains(driver.driver).move_to_element(els[floor]).click().perform()
        elif 35 <= floor <= 47:
            webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, -5).click().perform()
        else:
            webdriver.ActionChains(driver.driver).move_to_element(els[floor]).move_by_offset(0, 10).click().perform()
        frame = \
            driver.get_elements((By.CSS_SELECTOR, 'body > div.mfp-wrap.mfp-close-btn-in.mfp-auto-cursor.mfp-ready '
                                                  '> div > div.mfp-content > div > iframe'))[0]
        driver.driver.switch_to.frame(frame)
        hints = driver.get_elements((By.CSS_SELECTOR, '#body_hint > div'))

