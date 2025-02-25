# kocrd/system/ui.py
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from kocrd.system.ui.document_ui import DocumentUI
from kocrd.system.ui.monitoring_ui import MonitoringUI
from kocrd.system.ui.menubar_ui import Menubar
from kocrd.system.ui.messagebox_ui import MessageBoxUI
from kocrd.system.ui.preferenceswindow_ui import Preferenceswindow
from kocrd.system.config.config import UIConfig
from kocrd.system.config.config import Config

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.monitoring_ui = MonitoringUI(self)  # MonitoringUISystem 인스턴스 생성
        self.menubar = Menubar(self)
        self.messagebox_ui = MessageBoxUI(self.config) #Config 인스턴스 전달
        self.document_ui = DocumentUI(self)  # DocumentUI 인스턴스 생성
        self.preferences_window = Preferenceswindow(self)
        self.config = UIConfig("config/ui.json")  # Config 인스턴스 생성
        self.min_width = 500  # 최소 너비
        self.min_height = 200  # 최소 높이
        self.set_window_size()  # 창 크기 설정
        self.init_ui()
        
    def set_window_size(self):
        """창 크기를 설정합니다."""
        width, height = self.config.get_window_size("01_u")  # 사용자 설정 크기 가져오기
        if width is None or height is None:
            width, height = self.config.get_window_default_size("01_m")  # 기본 크기 가져오기
        if width and height:
            self.resize(width, height)  # 창 크기 설정
        self.setMinimumSize(self.min_width, self.min_height)  # 최소 크기 설정

    def resizeEvent(self, event):
        """창 크기 변경 이벤트 처리."""
        size = event.size()
        self.config.set_window_size("01_u", size.width(), size.height())  # 변경된 크기 저장
        self.resize_ui_modules(size.width())  # UI 모듈 크기 조절

    def init_ui(self):
        self.document_ui.init_ui()
        self.monitoring_ui.init_ui()
        self.menubar.setup_menus()
        self.resize_ui_modules(self.width())  # 초기 UI 모듈 크기 설정

    def resize_ui_modules(self, window_width):
        """UI 모듈 크기를 조절합니다."""
        doc_width, _ = self.config.get_window_size("01_d")  # 사용자 설정 document_ui 너비 가져오기
        if doc_width is None:
            doc_width, _ = self.config.get_window_default_size("01_d")  # 기본 document_ui 너비 가져오기

        mon_width, _ = self.config.get_window_size("01_mo")  # 사용자 설정 monitoring_ui 너비 가져오기
        if mon_width is None:
            mon_width, _ = self.config.get_window_default_size("01_mo.get")  # 기본 monitoring_ui 너비 가져오기

        if doc_width and mon_width:
            total_width = doc_width + mon_width
            doc_ratio = doc_width / total_width
            mon_ratio = mon_width / total_width

            available_width = window_width - 10  # 여백 고려
            new_doc_width = int(available_width * doc_ratio)
            new_mon_width = int(available_width * mon_ratio)

            self.document_ui.resize(new_doc_width, self.height())
            self.monitoring_ui.resize(new_mon_width, self.height())

    def closeEvent(self, event):
        self.messagebox_ui.closeEvent(event)
        event.accept()

    def show_preferences_window(self):
        self.preferences_window.show()

    def show_error_message(self, message):
        QMessageBox.critical(None, self.config.coll_text("UI", "012"), message)

    def show_question_message(self, message):
        reply = QMessageBox.question(None, self.config.coll_text("UI", "011"), message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply

    def show_information_message(self, message):
        QMessageBox.information(None, self.config.coll_text("UI", "006"), message)

    def show_warning_message(self, message):
        QMessageBox.warning(None, self.config.coll_text("UI", "011"), message)

    def show_confirmation_message(self, message):
        reply = QMessageBox.question(None, self.config.coll_text("UI", "011"), message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes