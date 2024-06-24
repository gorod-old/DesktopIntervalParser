from random import uniform
from time import sleep, time

from PyQt5.QtCore import QThread
from cffi.backend_ctypes import unicode
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from MessagePack.message import err_log
from WebDriverPack import WebDriver
from WebDriverPack.webDriver import try_func, timer_func
from g_gspread import update_sheet_data as gspread_update
from bs4 import BeautifulSoup as Bs
import numpy as np

HEADLESS = True
SITE_NAME = 'ЖК Солнечный город'
SITE_URL = 'https://solnechniy-gorod.ru/apartments/'
SPREADSHEET_ID = '11P-3bzliymAHrf_ESGeyIiQQM8FQgqC-GAGtd3mqKX4'  # заказчика
SHEET_ID = 0  # заказчика
SHEET_NAME = 'Лист1'  # заказчика
HEADER = ['Дом', 'Подъезд', 'Этаж', 'Тип', '№ квартиры', 'Площадь', 'Цена']

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
            #     sleep(10)
            #     sel = '#main-wrapper > div > div.current-view-sides > div.current-view-right > ' \
            #           'div.current-view-content > div > div > div.simplebar-wrapper > div.simplebar-mask > div > div ' \
            #           '> div > div > div > a '
            #     self.driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
            #     els = self.driver.get_elements((By.CSS_SELECTOR, sel))
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
    sleep(10)
    webdriver.ActionChains(driver.driver).scroll_by_amount(0, 180).perform()
    sel = 'body > section > div > div.crm > iframe'
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    iframe = driver.get_element((By.CSS_SELECTOR, sel))
    driver.driver.switch_to.frame(iframe)
    sleep(1)
    sel = '#main-wrapper > div > div.current-view-sides > div.current-view-right > div.current-view-content > div > ' \
          'div > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div > a '
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    el = driver.get_element((By.CSS_SELECTOR, sel))
    webdriver.ActionChains(driver.driver).move_to_element_with_offset(el, 100, 100).pause(3).click().perform()
    sleep(1)
    sel = '#main-wrapper > div > div.current-view-sides > div.current-view-right > div.filters-navigation > div > ul ' \
          '> li:nth-child(1) > a '
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    el = driver.get_element((By.CSS_SELECTOR, sel))
    webdriver.ActionChains(driver.driver).move_to_element(el).pause(3).click().perform()
    sleep(1)
    sel = '#main-wrapper > div > div.current-view-sides > div.current-view-right > div.current-view-content > div > ' \
          'div > div > div > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div > a '
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    el = driver.get_element((By.CSS_SELECTOR, sel))
    webdriver.ActionChains(driver.driver).move_to_element_with_offset(el, 100, 100).pause(3).click().perform()
    sleep(1)
    # планировки
    sel = '#main-wrapper > div > div.current-view-sides > div.current-view-right > div.filters-navigation > div > div ' \
          '> li:nth-child(3) '
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    bt = driver.get_element((By.CSS_SELECTOR, sel))
    webdriver.ActionChains(driver.driver).move_to_element(bt).pause(3).click().perform()
    # dropdown
    sel = '#main-wrapper > div > div.macro-widget-navigation > div.catalog-dropdown.widgets-nav-complexes.dropdown'
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    dropdown = driver.get_element((By.CSS_SELECTOR, sel))
    webdriver.ActionChains(driver.driver).move_to_element(dropdown).pause(3).click().perform()
    # dropdown items
    sel = '#main-wrapper > div > div.macro-widget-navigation > ' \
          'div.catalog-dropdown.widgets-nav-complexes.dropdown.opened > div:nth-child(2) > ul > li '
    driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
    d_items = driver.get_elements((By.CSS_SELECTOR, sel))
    for i in range(2, len(d_items)):
        print('d_item num:', i)
        if not app.run:
            return None
        webdriver.ActionChains(driver.driver).move_to_element(d_items[i]).pause(3).click().perform()
        sleep(3)
        sel = '#main-wrapper > div > div.current-view-sides > div.current-view-right > div.current-view-content > div ' \
              '> div > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div > div > a '
        driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
        els = driver.get_elements((By.CSS_SELECTOR, sel))
        print('els:', len(els))
        for k in range(len(els)):
            if not app.run:
                return None
            webdriver.ActionChains(driver.driver).move_to_element(els[k]).pause(1).click().perform()
            sleep(2)
            xpath = "//div[contains(text(), 'Свободные варианты на')]/following::div[contains(@class, " \
                    "'custom-scroll-md-default')]/div "
            driver.waiting_for_element((By.XPATH, xpath), 5)
            flat_els = driver.get_elements((By.XPATH, xpath))
            if len(flat_els) == 0:
                print('one flat')
                sel = '#main-wrapper > div > div.object-modal > div.object-modal__window > div.object-modal__content ' \
                      '> div > div.object-view-content.simplebar-scrollable-y > div.simplebar-wrapper > ' \
                      'div.simplebar-mask > div > div > div > div > div.object-view-content__desc > ' \
                      'div.object-view-content__desc-labels > div '
                driver.waiting_for_element((By.CSS_SELECTOR, sel), 5)
                flat_els = driver.get_elements((By.CSS_SELECTOR, sel))
            print('len els:', len(flat_els))
            for fel in flat_els:
                if not app.run:
                    return None
                if len(flat_els) > 1:
                    webdriver.ActionChains(driver.driver).move_to_element(fel).pause(1).click().perform()
                    sleep(1)
                house_, ent_, floor_, type_, flat_, area_, price_ = "", "", "", "", "", "", ""
                try:
                    s = 'div.object-view-content__desc-address-wrap '
                    obj = driver.get_element((By.CSS_SELECTOR, s))
                    text = obj.text.strip().lower().replace('"', '')
                    # print(text)
                    house_ = 'ЖК "Солнечный город"' + text.split('жк солнечный город')[2].split('\n')[0].strip()
                    floor_ = text.split('этаж №')[1].strip().replace('⁨', '').replace('⁩', '')
                    ent_ = text.split('подъезд №')[1].split('этаж')[0].replace('⁨', '').replace('⁩', '')\
                        .replace(',', '').strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [house_, floor_]', str(e))
                try:
                    s = '#main-wrapper > div > div.object-modal > div.object-modal__window > ' \
                        'div.object-modal__content > div > div.object-view-content.simplebar-scrollable-y > ' \
                        'div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > ' \
                        'div.object-view-content__desc > div.object-view-content__desc-wrap > ' \
                        'div.object-view-content__desc-info > div.d-flex.f-column.row-gap-4 > ' \
                        'div.object-view-content__desc-title > span.object-view-content__desc-name '
                    text = driver.get_element((By.CSS_SELECTOR, s)).text.strip()
                    type_ = text.split('№')[0].strip().replace('⁨', '').replace('⁩', '')
                    flat_ = text.split('№')[1].strip().replace('⁨', '').replace('⁩', '')
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [type_, flat_]', str(e))
                try:
                    s = '#main-wrapper > div > div.object-modal > div.object-modal__window > ' \
                        'div.object-modal__content > div > div.object-view-content.simplebar-scrollable-y > ' \
                        'div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > ' \
                        'div.object-view-content__desc > div.object-view-content__desc-wrap > ' \
                        'div.object-view-content__desc-info > div.d-flex.f-column.row-gap-4 > ' \
                        'div.object-view-content__desc-title > span.object-view-content__desc-area '
                    area_ = driver.get_element((By.CSS_SELECTOR, s)).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [area_]', str(e))
                try:
                    s = '#main-wrapper > div > div.object-modal > div.object-modal__window > ' \
                        'div.object-modal__content > div > div.object-view-content.simplebar-scrollable-y > ' \
                        'div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > ' \
                        'div.object-view-content__desc > div.object-view-content__desc-wrap > ' \
                        'div.object-view-content__desc-price > div > div.object-view-content__desc-price-info-price '
                    price_ = driver.get_element((By.CSS_SELECTOR, s)).text.strip()
                except Exception as e:
                    err_log(SITE_NAME + ' pars_data [price_]', str(e))
                row = [house_, ent_, floor_, type_, flat_, area_, price_]
                parser.add_row_info(row)
            # close button
            try:
                sel = '#main-wrapper > div > div.object-modal > div.object-modal__window > ' \
                      'div.object-modal__header > div '
                driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
                close = driver.get_element((By.CSS_SELECTOR, sel))
                print(close)
                webdriver.ActionChains(driver.driver).move_to_element(close).pause(5).click().perform()
                sleep(1)
            except Exception as e:
                print(str(e))

        webdriver.ActionChains(driver.driver).move_to_element(dropdown).pause(3).click().perform()
        sel = '#main-wrapper > div > div.macro-widget-navigation > ' \
              'div.catalog-dropdown.widgets-nav-complexes.dropdown.opened > div:nth-child(2) > ul > li '
        driver.waiting_for_element((By.CSS_SELECTOR, sel), 20)
        d_items = driver.get_elements((By.CSS_SELECTOR, sel))
    print('end')
    return data
