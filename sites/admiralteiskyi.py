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
SITE_NAME = 'ЖК Адмиралтейский'
SITE_URL = 'https://xn--80aplr0a.xn--p1ai/objects/'
SPREADSHEET_ID = '1dNrDABiT7Uk4IKLJOwSfwtuCvE3q0P_2LFY8ARl1uwg'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
# SPREADSHEET_ID = '1-UWakr2Y9tjlzXW857rp8PXcHEYHcADdEcJTUq3Q51I'  # мой
# SHEET_ID = 0  # мой
# SHEET_NAME = 'Лист1'  # мой
HEADER = ['Дом', 'Этаж', 'Квартира', 'Комнат', 'Площадь', 'Цена']

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
                els = self.driver.get_elements((By.CSS_SELECTOR, 'body > div.l-wrap.compensate-for-scrollbar > '
                                                                 'div.middle > div > section > div > div > div > div '
                                                                 '> div.object__left.col-md-4.col-lg-auto > a'))
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
    # driver.driver.maximize_window()
    objects = driver.get_elements((By.CSS_SELECTOR, 'body > div.l-wrap.compensate-for-scrollbar > div.middle > div > '
                                                    'section > div > div > div > div > '
                                                    'div.object__left.col-md-4.col-lg-auto > a'))
    parser.info_msg(f'Объекты: {len(objects)}')
    urls = []
    for obj in objects:
        url = obj.get_attribute('href')
        urls.append(url)

    for url in urls:
        if not app.run:
            return None
        # url = urls[-1]
        parser.info_msg(f'url: {url}')
        driver.get_page(url)
        sleep(1)
        els = driver.get_elements((By.CSS_SELECTOR, '#my-map > svg > g > path'))
        parser.info_msg(f'Этажи: {len(els)}')
        rng = len(els)
        for floor in range(0, rng, 1):
            if not app.run:
                return None
            h, f = '', ''
            for i in range(3):
                if 0 <= floor <= 1:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor]).pause(1).move_by_offset(0, 5).click().perform()
                if 19 <= floor <= 21:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor]).pause(1).move_by_offset(0, -10).click().perform()
                else:
                    webdriver.ActionChains(driver.driver).move_to_element(els[floor]).pause(1).move_by_offset(0, 0).click().perform()
                sleep(5)

                try:
                    h = url.split('/')[-2]
                    driver.waiting_for_element((By.XPATH, '//*[@id="result"]/div/div/div[1]/div[2]/span'), 10)
                    title = driver.get_element((By.XPATH, '//*[@id="result"]/div/div/div[1]/div[2]/span')).text.strip()
                    f = title.split('План')[1].split('-')[0].strip()
                    els_ = driver.get_elements((By.XPATH, '//area[contains(@data-key,"area")]'))
                    parser.info_msg(f'Дом: {h}, Этаж: {f}, Индекс: {floor}, Квартиры: {len(els_)}')
                    break
                except Exception as e:
                    print('error')
                    driver.get_page(url)
                    sleep(1)
                    els = driver.get_elements((By.CSS_SELECTOR, '#my-map > svg > g > path'))
                    err_log(SITE_NAME + ' pars_data [Дом, Этаж]', str(e))
                    pass

            try:
                map_ = driver.get_element((By.XPATH, '//*[@id="result"]/div/div/div[2]'))
                driver.driver.execute_script("arguments[0].scrollIntoView(false);", map_)
                sleep(1)
                action = webdriver.ActionChains(driver.driver)
                action.move_to_element(map_).move_by_offset(440, -150).pause(1).perform()
                # print('check1')
                get_row_data(parser, driver, h, f,)
                action.move_by_offset(200, 0).pause(1)
                action.move_by_offset(-100, 0).pause(1).perform()
                # print('check2')
                get_row_data(parser, driver, h, f,)
                action.move_by_offset(200, 0).pause(1)
                action.move_by_offset(-100, 350).pause(1).perform()
                # print('check3')
                get_row_data(parser, driver, h, f, )
                action.move_by_offset(120, 0).pause(1)
                action.move_by_offset(-400, 0).pause(1).perform()
                # print('check4')
                get_row_data(parser, driver, h, f,)
                action.move_by_offset(400, 0).pause(1)
                action.move_by_offset(-550, 0).pause(1).perform()
                # print('check5')
                get_row_data(parser, driver, h, f)
                action.move_by_offset(550, 0).pause(1)
                action.move_by_offset(-650, 0).pause(1).perform()
                # print('check6')
                get_row_data(parser, driver, h, f)
                action.move_by_offset(650, 0).pause(1)
                action.move_by_offset(-800, 0).pause(1).perform()
                # print('check7')
                get_row_data(parser, driver, h, f)
                action.move_by_offset(800, 0).pause(1)
                action.move_by_offset(-940, 0).pause(1).perform()
                # print('check8')
                get_row_data(parser, driver, h, f)
                action.move_by_offset(940, 0).pause(1)
                action.move_by_offset(-1050, 0).pause(1).perform()
                # print('check9')
                get_row_data(parser, driver, h, f)
                action.move_by_offset(1050, 0).pause(1)
                action.move_by_offset(-1200, 0).pause(1).perform()
                # print('check10')
                get_row_data(parser, driver, h, f)
                action.move_by_offset(-100, 0).pause(1)
                action.move_by_offset(600, -300).pause(1).perform()
                # print('check14')
                get_row_data(parser, driver, h, f)
                action.move_to_element(map_).move_by_offset(0, -350).pause(1)
                action.move_to_element(map_).move_by_offset(-100, -150).pause(1).perform()
                # print('check13')
                get_row_data(parser, driver, h, f)
                action.move_to_element(map_).move_by_offset(0, -350).pause(1)
                action.move_to_element(map_).move_by_offset(-250, -150).pause(1).perform()
                # print('check12')
                get_row_data(parser, driver, h, f)
                action.move_to_element(map_).move_by_offset(0, -350).pause(1)
                action.move_to_element(map_).move_by_offset(-450, -150).pause(1).perform()
                # print('check11')
                get_row_data(parser, driver, h, f)
                pass
            except Exception as e:
                err_log(SITE_NAME + f' pars_data [квартиры]' + f' дом {h} этаж {f}', str(e))
                pass
            # break
    return data


@try_func
def get_row_data(parser, driver, h, f):
    row = [h, f]
    flat_, type_, area_, price_ = '', '', '', ''
    els_ = []
    try:
        els_ = driver.get_elements((By.CSS_SELECTOR, 'div.popover__left'))
    except Exception as e:
        err_log(SITE_NAME + ' get_flat_info [els_]', str(e))
    if len(els_) > 0:
        for el in els_:
            text = el.text.lower().replace('\n', ' ').strip()
            print(text)
            if text != '' and 'свободна' in text:
                try:
                    flat_ = text.split('квартира ')[1].split(' ')[0].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [квартира]', str(e))
                try:
                    type_ = text.split('количество комнат: ')[1].split(' ')[0].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [комнат]', str(e))
                try:
                    area_ = text.split('общая площадь: ')[1].split(' ')[0].strip()
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [площадь]', str(e))
                try:
                    price_ = text.split('стоимость: ')[1].split('р.')[0].strip() + ' р.'
                except Exception as e:
                    err_log(SITE_NAME + ' get_flat_info [цена]', str(e))
                row.extend([flat_, type_, area_, price_])
                parser.add_row_info(row, h, f)




