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
from sites.jk_zelbulvar_rf2 import SiteParser as Parser_4
from sites.eskadra_development_ru import SiteParser as Parser_5
# from sites.test import SiteParser as Parser_5
from sites.seasons_25_ru2 import SiteParser as Parser_6
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
# from sites.fiolent import SiteParser as Parser_21
from sites.samolet import SiteParser as Parser_21
from sites.jk_garmonia import SiteParser as Parser_22
from sites.jk_chayka import SiteParser as Parser_23
from sites.jk_yujniy import SiteParser as Parser_24
# from sites.jk_dom_so_lvom import SiteParser as Parser_25
from sites.jk_zolotoy_rog import SiteParser as Parser_25
from sites.jk_panorama import SiteParser as Parser_26
from sites.leo_development_ru import SiteParser as Parser_27
from sites.jk_singapur import SiteParser as Parser_28
from sites.suprim_dom import SiteParser as Parser_29
from sites.jk_legenda import SiteParser as Parser_30
from sites.jk_amurskiy import SiteParser as Parser_31
from sites.jk_sunrise import SiteParser as Parser_32
from sites.jk_med import SiteParser as Parser_33
from sites.jk_fiord import SiteParser as Parser_34
from sites.jk_inlove import SiteParser as Parser_35
from sites.jk_voshod import SiteParser as Parser_36
from sites.jk_istoricheskiy import SiteParser as Parser_37
from sites.atlantics_sity import SiteParser as Parser_38
from sites.jk_eloviy import SiteParser as Parser_39
from sites.jk_meridiany_ulissa import SiteParser as Parser_40
from sites.jk_cherniahovskogo import SiteParser as Parser_41
from sites.jk_solnechniy_gorod import SiteParser as Parser_42
from sites.jk_lisapark import SiteParser as Parser_43
from sites.jk_stark import SiteParser as Parser_44
from sites.kvartirogramma import SiteParser as Parser_45
from sites.jk_flagman import SiteParser as Parser_46
from sites.jk_7ya import SiteParser as Parser_47
from sites.jk_andersen import SiteParser as Parser_48
from sites.jk_vesna import SiteParser as Parser_49
from sites.jk_five import SiteParser as Parser_50
from sites.jk_kvartal_chehova import SiteParser as Parser_51


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
            self.label_22.text(): Parser_22,
            self.label_23.text(): Parser_23,
            self.label_24.text(): Parser_24,
            self.label_25.text(): Parser_25,
            self.label_26.text(): Parser_26,
            self.label_27.text(): Parser_27,
            self.label_28.text(): Parser_28,
            self.label_29.text(): Parser_29,
            self.label_30.text(): Parser_30,
            self.label_31.text(): Parser_31,
            self.label_32.text(): Parser_32,
            self.label_33.text(): Parser_33,
            self.label_34.text(): Parser_34,
            self.label_35.text(): Parser_35,
            self.label_36.text(): Parser_36,
            self.label_37.text(): Parser_37,
            self.label_38.text(): Parser_38,
            self.label_39.text(): Parser_39,
            self.label_40.text(): Parser_40,
            self.label_41.text(): Parser_41,
            self.label_42.text(): Parser_42,
            self.label_43.text(): Parser_43,
            self.label_44.text(): Parser_44,
            self.label_45.text(): Parser_45,
            self.label_46.text(): Parser_46,
            self.label_47.text(): Parser_47,
            self.label_48.text(): Parser_48,
            self.label_49.text(): Parser_49,
            self.label_50.text(): Parser_50,
            self.label_51.text(): Parser_51,
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
        self.siteButton_22.clicked.connect(self._site_click_22)
        self.siteButton_23.clicked.connect(self._site_click_23)
        self.siteButton_24.clicked.connect(self._site_click_24)
        self.siteButton_25.clicked.connect(self._site_click_25)
        self.siteButton_26.clicked.connect(self._site_click_26)
        self.siteButton_27.clicked.connect(self._site_click_27)
        self.siteButton_28.clicked.connect(self._site_click_28)
        self.siteButton_29.clicked.connect(self._site_click_29)
        self.siteButton_30.clicked.connect(self._site_click_30)
        self.siteButton_31.clicked.connect(self._site_click_31)
        self.siteButton_32.clicked.connect(self._site_click_32)
        self.siteButton_33.clicked.connect(self._site_click_33)
        self.siteButton_34.clicked.connect(self._site_click_34)
        self.siteButton_35.clicked.connect(self._site_click_35)
        self.siteButton_36.clicked.connect(self._site_click_36)
        self.siteButton_37.clicked.connect(self._site_click_37)
        self.siteButton_38.clicked.connect(self._site_click_38)
        self.siteButton_39.clicked.connect(self._site_click_39)
        self.siteButton_40.clicked.connect(self._site_click_40)
        self.siteButton_41.clicked.connect(self._site_click_41)
        self.siteButton_42.clicked.connect(self._site_click_42)
        self.siteButton_43.clicked.connect(self._site_click_43)
        self.siteButton_44.clicked.connect(self._site_click_44)
        self.siteButton_45.clicked.connect(self._site_click_45)
        self.siteButton_46.clicked.connect(self._site_click_46)
        self.siteButton_47.clicked.connect(self._site_click_47)
        self.siteButton_48.clicked.connect(self._site_click_48)
        self.siteButton_49.clicked.connect(self._site_click_49)
        self.siteButton_50.clicked.connect(self._site_click_50)
        self.siteButton_51.clicked.connect(self._site_click_51)

        self.statusBar().showMessage("📞telegram: @gorod_old    💰YooMoney(карта): 5599 0050 9705 4931")

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
        self.label_22.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_22.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_23.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_23.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_24.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_24.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_25.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_25.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_26.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_26.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_27.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_27.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_28.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_28.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_29.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_29.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_30.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_30.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_31.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_31.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_32.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_32.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_33.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_33.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_34.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_34.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_35.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_35.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_36.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_36.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_37.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_37.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_38.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_38.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_39.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_39.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_40.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_40.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_41.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_41.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_42.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_42.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_43.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_43.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_44.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_44.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_45.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_45.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_46.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_46.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_47.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_47.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_48.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_48.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_49.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_49.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_50.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_50.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
        self.label_51.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_51.text() in self._sites else
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

    def _site_click_22(self):
        if self.label_22.text() in self._sites:
            self._sites.remove(self.label_22.text())
        else:
            self._sites.append(self.label_22.text())
        self._save_app_setup()
        self.label_22.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_22.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_23(self):
        if self.label_23.text() in self._sites:
            self._sites.remove(self.label_23.text())
        else:
            self._sites.append(self.label_23.text())
        self._save_app_setup()
        self.label_23.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_23.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_24(self):
        if self.label_24.text() in self._sites:
            self._sites.remove(self.label_24.text())
        else:
            self._sites.append(self.label_24.text())
        self._save_app_setup()
        self.label_24.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_24.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_25(self):
        if self.label_25.text() in self._sites:
            self._sites.remove(self.label_25.text())
        else:
            self._sites.append(self.label_25.text())
        self._save_app_setup()
        self.label_25.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_25.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_26(self):
        if self.label_26.text() in self._sites:
            self._sites.remove(self.label_26.text())
        else:
            self._sites.append(self.label_26.text())
        self._save_app_setup()
        self.label_26.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_26.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_27(self):
        if self.label_27.text() in self._sites:
            self._sites.remove(self.label_27.text())
        else:
            self._sites.append(self.label_27.text())
        self._save_app_setup()
        self.label_27.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_27.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_28(self):
        if self.label_28.text() in self._sites:
            self._sites.remove(self.label_28.text())
        else:
            self._sites.append(self.label_28.text())
        self._save_app_setup()
        self.label_28.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_28.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_29(self):
        if self.label_29.text() in self._sites:
            self._sites.remove(self.label_29.text())
        else:
            self._sites.append(self.label_29.text())
        self._save_app_setup()
        self.label_29.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_29.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_30(self):
        if self.label_30.text() in self._sites:
            self._sites.remove(self.label_30.text())
        else:
            self._sites.append(self.label_30.text())
        self._save_app_setup()
        self.label_30.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_30.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_31(self):
        if self.label_31.text() in self._sites:
            self._sites.remove(self.label_31.text())
        else:
            self._sites.append(self.label_31.text())
        self._save_app_setup()
        self.label_31.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_31.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_32(self):
        if self.label_32.text() in self._sites:
            self._sites.remove(self.label_32.text())
        else:
            self._sites.append(self.label_32.text())
        self._save_app_setup()
        self.label_32.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_32.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_33(self):
        if self.label_33.text() in self._sites:
            self._sites.remove(self.label_33.text())
        else:
            self._sites.append(self.label_33.text())
        self._save_app_setup()
        self.label_33.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_33.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_34(self):
        if self.label_34.text() in self._sites:
            self._sites.remove(self.label_34.text())
        else:
            self._sites.append(self.label_34.text())
        self._save_app_setup()
        self.label_34.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_34.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_35(self):
        if self.label_35.text() in self._sites:
            self._sites.remove(self.label_35.text())
        else:
            self._sites.append(self.label_35.text())
        self._save_app_setup()
        self.label_35.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_35.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_36(self):
        if self.label_36.text() in self._sites:
            self._sites.remove(self.label_36.text())
        else:
            self._sites.append(self.label_36.text())
        self._save_app_setup()
        self.label_36.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_36.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_37(self):
        if self.label_37.text() in self._sites:
            self._sites.remove(self.label_37.text())
        else:
            self._sites.append(self.label_37.text())
        self._save_app_setup()
        self.label_37.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_37.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_38(self):
        if self.label_38.text() in self._sites:
            self._sites.remove(self.label_38.text())
        else:
            self._sites.append(self.label_38.text())
        self._save_app_setup()
        self.label_38.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_38.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_39(self):
        if self.label_39.text() in self._sites:
            self._sites.remove(self.label_39.text())
        else:
            self._sites.append(self.label_39.text())
        self._save_app_setup()
        self.label_39.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_39.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_40(self):
        if self.label_40.text() in self._sites:
            self._sites.remove(self.label_40.text())
        else:
            self._sites.append(self.label_40.text())
        self._save_app_setup()
        self.label_40.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_40.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_41(self):
        if self.label_41.text() in self._sites:
            self._sites.remove(self.label_41.text())
        else:
            self._sites.append(self.label_41.text())
        self._save_app_setup()
        self.label_41.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_41.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_42(self):
        if self.label_42.text() in self._sites:
            self._sites.remove(self.label_42.text())
        else:
            self._sites.append(self.label_42.text())
        self._save_app_setup()
        self.label_42.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_42.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_43(self):
        if self.label_43.text() in self._sites:
            self._sites.remove(self.label_43.text())
        else:
            self._sites.append(self.label_43.text())
        self._save_app_setup()
        self.label_43.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_43.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_44(self):
        if self.label_44.text() in self._sites:
            self._sites.remove(self.label_44.text())
        else:
            self._sites.append(self.label_44.text())
        self._save_app_setup()
        self.label_44.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_44.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_45(self):
        if self.label_45.text() in self._sites:
            self._sites.remove(self.label_45.text())
        else:
            self._sites.append(self.label_45.text())
        self._save_app_setup()
        self.label_45.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_45.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_46(self):
        if self.label_46.text() in self._sites:
            self._sites.remove(self.label_46.text())
        else:
            self._sites.append(self.label_46.text())
        self._save_app_setup()
        self.label_46.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_46.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_47(self):
        if self.label_47.text() in self._sites:
            self._sites.remove(self.label_47.text())
        else:
            self._sites.append(self.label_47.text())
        self._save_app_setup()
        self.label_47.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_47.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_48(self):
        if self.label_48.text() in self._sites:
            self._sites.remove(self.label_48.text())
        else:
            self._sites.append(self.label_48.text())
        self._save_app_setup()
        self.label_48.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_48.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_49(self):
        if self.label_49.text() in self._sites:
            self._sites.remove(self.label_49.text())
        else:
            self._sites.append(self.label_49.text())
        self._save_app_setup()
        self.label_49.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_49.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_50(self):
        if self.label_50.text() in self._sites:
            self._sites.remove(self.label_50.text())
        else:
            self._sites.append(self.label_50.text())
        self._save_app_setup()
        self.label_50.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_50.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')

    def _site_click_51(self):
        if self.label_51.text() in self._sites:
            self._sites.remove(self.label_51.text())
        else:
            self._sites.append(self.label_51.text())
        self._save_app_setup()
        self.label_51.setStyleSheet(
            'background-color: rgb(149, 255, 188); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;'
            if self.label_51.text() in self._sites else
            'background-color: rgb(255, 164, 231); color: rgb(0, 0, 0); padding: 0 5px; border: 1px solid;')
