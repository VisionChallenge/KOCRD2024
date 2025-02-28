# kocrd/system/ui.py
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from kocrd.system.ui.document_ui import DocumentUI
from kocrd.system.ui.monitoring_ui import MonitoringUI
from kocrd.system.ui.menubar_ui import Menubar
from kocrd.system.ui.messagebox_ui import MessageBoxUI
from kocrd.system.ui.preferenceswindow_ui import Preferenceswindow
from kocrd.system.config.config import UIConfig
from kocrd.system.config.config import Config
from kocrd.system.ui.menubar_ui import Menubar
from kocrd.system.database_manager import DatabaseManager
from kocrd.system.document_manager import DocumentManager
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

class MainWindow(QMainWindow, QObject):
    document_updated = pyqtSignal(str, int)
    progress_changed = pyqtSignal(str, int)

    def __init__(self, config_file="config/ui.json", database_manager=None, document_manager=None):
        super().__init__()
        self.config = Config(config_file)
        self.database_manager = database_manager or DatabaseManager()
        self.document_manager = document_manager or DocumentManager()
        self.init_ui()

    def init_ui(self):
        self.monitoring_ui = MonitoringUI(self, self.config.ui)
        self.document_ui = DocumentUI(self, self.config.ui)
        self.menubar = Menubar(self)
        self.messagebox_ui = MessageBoxUI(self.config)
        self.preferences_window = Preferenceswindow(self)
        self.min_width, self.min_height = 500, 200
        self.set_window_size()
        self.document_ui.init_ui()
        self.monitoring_ui.init_ui()
        self.menubar.setup_menus()
        self.resize_ui_modules(self.width())

        # 신호 연결
        self.document_updated.connect(self.handle_document_update)
        self.progress_changed.connect(self.handle_progress_change)

    def update_document(self, text, number):
        self.document_updated.emit(text, number)

    def update_progress(self, text, number):
        self.progress_changed.emit(text, number)

    @pyqtSlot(str, int)
    def handle_document_update(self, text, number):
        print(f"문서 업데이트 신호 수신: {text}, {number}")
        # 문서 업데이트 처리

    @pyqtSlot(str, int)
    def handle_progress_change(self, text, number):
        print(f"진행률 변경 신호 수신: {text}, {number}")
        # 진행률 업데이트 처리

    def set_window_size(self):
        width, height = self.config.get_window_size("01_u")
        if width is None or height is None:
            width, height = self.config.get_window_default_size("01_m")
        if width and height:
            self.resize(width, height)
        self.setMinimumSize(self.min_width, self.min_height)

    def resizeEvent(self, event):
        size = event.size()
        self.config.set_window_size("01_u", size.width(), size.height())
        self.resize_ui_modules(size.width())

    def resize_ui_modules(self, window_width):
        sizes = self.config.calculate_module_sizes(window_width)
        if sizes:
            self.document_ui.resize(sizes["document_width"], self.height())
            self.monitoring_ui.resize(sizes["monitoring_width"], self.height())

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

    def get_managers(self):
        return self.config.database_manager, self.config.document_manager
