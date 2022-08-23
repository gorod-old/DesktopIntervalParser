import os
import subprocess

import schedule
import design
from datetime import datetime
from time import sleep, perf_counter
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QListWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from AsyncProcessPack import AsyncProcess
from MessagePack import print_info_msg
from WebDriverPack.webDriver import convert_sec_to_time_string
from WinSoundPack import beep
from save_data import save_json, get_json_data_from_file
from sites.brusnika_dom_ru import SiteParser as Parser_1
from sites.jk_ajax_rf import SiteParser as Parser_2
from sites.jk_vostochniy_rf import SiteParser as Parser_3
from sites.jk_zelbulvar_rf import SiteParser as Parser_4
from sites.eskadra_development_ru import SiteParser as Parser_5
from sites.seasons_25_ru import SiteParser as Parser_6
from sites.jk_juravli_rf import SiteParser as Parser_7
from sites.jk_zolotaya_dolina_rf import SiteParser as Parser_8
from sites.jk_lastochka_ru import SiteParser as Parser_9
from sites.bosforskiy_park import SiteParser as Parser_10
from sites.jk_leto import SiteParser as Parser_11
from sites.vostochniy_luch import SiteParser as Parser_12
from sites.novojilovo import SiteParser as Parser_13
from sites.admiralteiskyi import SiteParser as Parser_14
from sites.klenovyi import SiteParser as Parser_15
from sites.dolina import SiteParser as Parser_16
from sites.emerald import SiteParser as Parser_17
from sites.domino import SiteParser as Parser_18
from sites.akvamarin import SiteParser as Parser_19
from sites.pribrejniy_dom import SiteParser as Parser_20
from sites.fiolent import SiteParser as Parser_21


class QTTimer(QThread):

    def __init__(self, app):
        super().__init__()
        self.start_time = 0
        self.app = app

    def run(self):
        self.start_time = perf_counter()
        self.app.startTime.setText(datetime.now().strftime('%H:%M:%S'))
        self.app.workTime.setText('00:00:00')
        while self.app.run:
            time = perf_counter() - self.start_time
            self.app.workTime.setText(self.app.convert_sec_to_time_string(time))
            sleep(1)
        print('stop timer')
        self.quit()


class ScheduleThread(QThread):
    about_time = pyqtSignal(int)

    def __init__(self, app):
        super().__init__()
        self.app = app
        print('start scheduler')

    def add_time(self, time: int):
        # schedule.every(time).minutes.do(
        schedule.every(time).hours.do(
            lambda: self.about_time.emit(time)
        )

    def run(self):
        while self.app.run:
            schedule.run_pending()
            sleep(1)
        schedule.jobs.clear()
        sleep(1)
        print('stop scheduler')
        self.quit()


class MainWindow(QMainWindow, design.Ui_MainWindow):

    def __init__(self, marker: str = ''):
        # Обязательно нужно вызвать метод супер класса
        QMainWindow.__init__(self)
        self.setupUi(self)

        # ToolTips stylesheet
        self.setStyleSheet("""QToolTip {
                            border: 1px solid black;
                            padding: 3px;
                            border-radius: 3px;
                            opacity: 200;
                        }""")

        self._parsers = {
            self.label_1.text(): Parser_1,
            self.label_2.text(): Parser_2,
            self.label_3.text(): Parser_3,
            self.label_4.text(): Parser_4,
            self.label_5.text(): Parser_5,
            self.label_6.text(): Parser_6,
            self.label_7.text(): Parser_7,
            self.label_8.text(): Parser_8,
            self.label_9.text(): Parser_9,
            self.label_10.text(): Parser_10,
            self.label_11.text(): Parser_11,
            self.label_12.text(): Parser_12,
            self.label_13.text(): Parser_13,
            self.label_14.text(): Parser_14,
            self.label_15.text(): Parser_15,
            self.label_16.text(): Parser_16,
            self.label_17.text(): Parser_17,
            self.label_18.text(): Parser_18,
            self.label_19.text(): Parser_19,
            self.label_20.text(): Parser_20,
            self.label_21.text(): Parser_21,
        }

        self._app_setup()
        self._cpu = os.cpu_count()
        self._run = False
        self._interval = 1
        self._interval_timer = None

        self._n_list = []  # список названий запущенных (работающих в данный момент) парсеров
        self._p_list = []  # список запущенных (работающих в данный момент) парсеров
        self._s_list = []  # in use stream numbers
        self._check_list = []  # список выбранных парсеров которые еще не запускались

        self.setWindowTitle(marker)  # Устанавливаем заголовок окна
        self.startTime.setText('00:00:00')
        self.workTime.setText('00:00:00')
        self.statusLabel.setText('ОСТАНОВЛЕН')
        self.statusLabel.setStyleSheet(
            'background-color: rgb(255, 255, 255); color: rgb(255, 74, 101); border: 1px solid;')
        self.startButton.clicked.connect(self._start_click)
        self.stopButton.clicked.connect(self._stop_click)
        self.comboBox.addItems(['1 час', '2 часа', '3 часа', '4 часа', '5 часов', '6 часов'])
        self.comboBox.currentTextChanged.connect(self._combobox_text_changed)
        self.siteButton_1.clicked.connect(self._site_click_1)
        self.siteButton_2.clicked.connect(self._site_click_2)
        self.siteButton_3.clicked.connect(self._site_click_3)
        self.siteButton_4.clicked.connect(self._site_click_4)
        self.siteButton_5.clicked.connect(self._site_click_5)
        self.siteButton_6.clicked.connect(self._site_click_6)
        self.siteButton_7.clicked.connect(self._site_click_7)
        self.siteButton_8.clicked.connect(self._site_click_8)
        self.siteButton_9.clicked.connect(self._site_click_9)
        self.siteButton_10.clicked.connect(self._site_click_10)
        self.siteButton_11.clicked.connect(self._site_click_11)
        self.siteButton_12.clicked.connect(self._site_click_12)
        self.siteButton_13.clicked.connect(self._site_click_13)
        self.siteButton_14.clicked.connect(self._site_click_14)
        self.siteButton_15.clicked.connect(self._site_click_15)
        self.siteButton_16.clicked.connect(self._site_click_16)
        self.siteButton_17.clicked.connect(self._site_click_17)
        self.siteButton_18.clicked.connect(self._site_click_18)
        self.siteButton_19.clicked.connect(self._site_click_19)
        self.siteButton_20.clicked.connect(self._site_click_20)
        self.siteButton_21.clicked.connect(self._site_click_21)

    @property
    def run(self):
        return self._run

    @classmethod
    def convert_sec_to_time_string(cls, seconds):
        """ Convert time value in seconds to time data string - 00:00:00"""
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%02d:%02d:%02d" % (hour, minutes, seconds)

    def _start_click(self):
        if self._run:
            return
        print('start')
        self._run = True
        # no sleep mode
        subprocess.call("powercfg -change -monitor-timeout-ac 0")
        subprocess.call("powercfg -change -disk-timeout-ac 0")
        subprocess.call("powercfg -change -standby-timeout-ac 0")
        # run scheduler
        self._i_timer()
        # run timer
        self.timer = QTTimer(self)
        self.timer.start()
        # set ui data
        AsyncProcess('reset UI', self._reset_ui, 1, (self, '_end_reset_ui'))

    def _stop_click(self):
        if not self._run:
            return
        print('stop')
        beep()
        self._run = False
        self._n_list.clear()
        self.statusLabel.setText('ОСТАНОВЛЕН')
        self.statusLabel.setStyleSheet(
            'background-color: rgb(255, 255, 255); color: rgb(255, 74, 101); border: 1px solid;')

    def closeEvent(self, event):
        print('close event')
        if self._run:
            button = QMessageBox.question(self, "Внимание!", "Текущие процессы парсинга будут остановлены! Продолжить?")
            if button == QMessageBox.Yes:
                self._stop_click()
                sleep(10)
                event.accept()
            else:
                event.ignore()

    def _combobox_text_changed(self):
        if self._run and self.comboBox.currentIndex() + 1 != self._interval:
            button = QMessageBox.question(self, "Внимание!", "Текущие процессы парсинга будут остановлены и "
                                                             "перезапущены для изменения интервала! Продолжить?")
            if button == QMessageBox.Yes:
                self._set_interval()
                self._stop_click()
                sleep(10)
                self._start_click()
            else:
                self.comboBox.setCurrentIndex(self._interval - 1)
        else:
            self._set_interval()

    def _set_interval(self):
        self._interval = self.comboBox.currentIndex() + 1
        print('выбран интервал:', self._interval,
              'час.' if self._interval == 1 else 'часа.' if self._interval < 5 else 'часов.')

    def _i_timer(self):
        self._interval_timer = ScheduleThread(self)
        self._interval_timer.about_time.connect(self._run_app)
        self._interval_timer.add_time(self._interval)
        self._interval_timer.start()

    def _reset_ui(self):
        self.statusLabel.setText('ЗАПУЩЕН')
        self.statusLabel.setStyleSheet(
            'background-color: rgb(255, 255, 255); color: rgb(85, 170, 127); border: 1px solid;')
        # self.resultListWidget.clear()

    def _end_reset_ui(self):
        self._run_app()

    def _run_app(self):
        # TODO: продумать логику замены или добавления парсеров при ограничении по CPU
        if not self._run:
            return
        beep()
        for name in self._sites:
            if len(self._check_list) < len(self._sites) and name not in self._check_list:
                self._check_list.append(name)

        if len(self._n_list) == 0:
            self._p_list.clear()
            self._s_list.clear()

        print_info_msg(f'cpu count: {self._cpu}, now running: {len(self._n_list)}')
        num = self._cpu - len(self._n_list)
        print_info_msg(f'number of free threads: {num}')
        for i in range(num):
            self._add_parser()

    def _add_parser(self):
        if len(self._check_list) == 0:
            print('All selected sites have been started and will be re-run the next time the interval is started.')
            return
        j = 0
        while j < len(self._check_list):
            name = self._check_list[j]
            if name not in self._n_list:
                stream = self._get_stream()
                self._n_list.append(name)
                self._p_list.append(self._parsers[name](self, name, stream))
                self._p_list[-1].start()
                self._check_list.remove(name)

                # add start info to console
                item = QListWidgetItem(f'старт {name}')
                item.setForeground(Qt.blue)
                self.resultListWidget.addItem(item)
                self.resultListWidget.scrollToBottom()
                break
            else:
                print(f'parser {name} is still running, cancel launch!')
            j += 1

    def next_parser(self, name, stream):
        # TODO: продумать логику замены или добавления парсеров при ограничении по CPU
        print(f'parser {name} - finished work')
        if not self._run:
            return
        if name in self._n_list:
            self._n_list.remove(name)
        if stream in self._s_list:
            self._s_list.remove(stream)
        print('running list:', self._n_list)
        self._add_parser()

    def _get_stream(self):
        for n in range(len(self._sites)):
            if n not in self._s_list:
                self._s_list.append(n)
                return n

    def parser_result(self, name, count, time_delta):
        end_time = datetime.now()
        time = convert_sec_to_time_string(time_delta)
        text = name + ': ' + str(count) + ' строк, время работы - ' + str(time) + ', ' + str(end_time)
        f = open("results.log", "a", encoding='ANSI')
        f.write(text + '\n')
        f.close()
        item = QListWidgetItem(text)
        if count == 0:
            item.setForeground(Qt.red)
        self.resultListWidget.addItem(item)
        self.resultListWidget.scrollToBottom()

    def _app_setup(self):
        if not os.path.exists('setup.json'):
            data = {
                'site_list': ''
            }
            save_json(data, file_name='setup')
        setup = get_json_data_from_file('setup.json')
        self._sites = setup.get('site_list').split('|')
        if self._sites[0] == '':
            self._sites = self._sites[1:]
        print(self._sites)
        self.siteInfoLabel.setText('Сайты для парсинга: ' + ', '.join(self._sites))
        self.label_1.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_1.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_2.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_2.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_3.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_3.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_4.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_4.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_5.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_5.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_6.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_6.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_7.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_7.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_8.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_8.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_9.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_9.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_10.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_10.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_11.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_11.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_12.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_12.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_13.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_13.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_14.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_14.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_15.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_15.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_16.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_16.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_17.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_17.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_18.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_18.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_19.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_19.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_20.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_20.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_21.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_21.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _save_app_setup(self):
        data = {
            'site_list': '|'.join(self._sites)
        }
        save_json(data, file_name='setup')
        self.siteInfoLabel.setText('Сайты для парсинга: ' + ', '.join(self._sites))

    def _site_click_1(self):
        if self.label_1.text() in self._sites:
            self._sites.remove(self.label_1.text())
        else:
            self._sites.append(self.label_1.text())
        self._save_app_setup()
        self.label_1.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_1.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_2(self):
        if self.label_2.text() in self._sites:
            self._sites.remove(self.label_2.text())
        else:
            self._sites.append(self.label_2.text())
        self._save_app_setup()
        self.label_2.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_2.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_3(self):
        if self.label_3.text() in self._sites:
            self._sites.remove(self.label_3.text())
        else:
            self._sites.append(self.label_3.text())
        self._save_app_setup()
        self.label_3.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_3.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_4(self):
        if self.label_4.text() in self._sites:
            self._sites.remove(self.label_4.text())
        else:
            self._sites.append(self.label_4.text())
        self._save_app_setup()
        self.label_4.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_4.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_5(self):
        if self.label_5.text() in self._sites:
            self._sites.remove(self.label_5.text())
        else:
            self._sites.append(self.label_5.text())
        self._save_app_setup()
        self.label_5.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_5.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_6(self):
        if self.label_6.text() in self._sites:
            self._sites.remove(self.label_6.text())
        else:
            self._sites.append(self.label_6.text())
        self._save_app_setup()
        self.label_6.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_6.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_7(self):
        if self.label_7.text() in self._sites:
            self._sites.remove(self.label_7.text())
        else:
            self._sites.append(self.label_7.text())
        self._save_app_setup()
        self.label_7.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_7.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_8(self):
        if self.label_8.text() in self._sites:
            self._sites.remove(self.label_8.text())
        else:
            self._sites.append(self.label_8.text())
        self._save_app_setup()
        self.label_8.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_8.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_9(self):
        if self.label_9.text() in self._sites:
            self._sites.remove(self.label_9.text())
        else:
            self._sites.append(self.label_9.text())
        self._save_app_setup()
        self.label_9.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_9.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_10(self):
        if self.label_10.text() in self._sites:
            self._sites.remove(self.label_10.text())
        else:
            self._sites.append(self.label_10.text())
        self._save_app_setup()
        self.label_10.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_10.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_11(self):
        if self.label_11.text() in self._sites:
            self._sites.remove(self.label_11.text())
        else:
            self._sites.append(self.label_11.text())
        self._save_app_setup()
        self.label_11.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_11.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_12(self):
        if self.label_12.text() in self._sites:
            self._sites.remove(self.label_12.text())
        else:
            self._sites.append(self.label_12.text())
        self._save_app_setup()
        self.label_12.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_12.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_13(self):
        if self.label_13.text() in self._sites:
            self._sites.remove(self.label_13.text())
        else:
            self._sites.append(self.label_13.text())
        self._save_app_setup()
        self.label_13.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_13.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_14(self):
        if self.label_14.text() in self._sites:
            self._sites.remove(self.label_14.text())
        else:
            self._sites.append(self.label_14.text())
        self._save_app_setup()
        self.label_14.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_14.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_15(self):
        if self.label_15.text() in self._sites:
            self._sites.remove(self.label_15.text())
        else:
            self._sites.append(self.label_15.text())
        self._save_app_setup()
        self.label_15.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_15.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_16(self):
        if self.label_16.text() in self._sites:
            self._sites.remove(self.label_16.text())
        else:
            self._sites.append(self.label_16.text())
        self._save_app_setup()
        self.label_16.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_16.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_17(self):
        if self.label_17.text() in self._sites:
            self._sites.remove(self.label_17.text())
        else:
            self._sites.append(self.label_17.text())
        self._save_app_setup()
        self.label_17.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_17.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_18(self):
        if self.label_18.text() in self._sites:
            self._sites.remove(self.label_18.text())
        else:
            self._sites.append(self.label_18.text())
        self._save_app_setup()
        self.label_18.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_18.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_19(self):
        if self.label_19.text() in self._sites:
            self._sites.remove(self.label_19.text())
        else:
            self._sites.append(self.label_19.text())
        self._save_app_setup()
        self.label_19.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_19.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_20(self):
        if self.label_20.text() in self._sites:
            self._sites.remove(self.label_20.text())
        else:
            self._sites.append(self.label_20.text())
        self._save_app_setup()
        self.label_20.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_20.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_21(self):
        if self.label_21.text() in self._sites:
            self._sites.remove(self.label_21.text())
        else:
            self._sites.append(self.label_21.text())
        self._save_app_setup()
        self.label_21.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_21.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')