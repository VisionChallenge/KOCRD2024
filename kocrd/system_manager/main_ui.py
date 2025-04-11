# kocrd/system/main_ui.py
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QSplitter, QProgressBar, QStatusBar
from kocrd.system_manager.ui.document_ui import DocumentUI
from kocrd.system_manager.ui.monitoring_ui import MonitoringUI
from kocrd.system_manager.ui.menubar_ui import Menubar
from kocrd.system_manager.ui.preferenceswindow_ui import Preferenceswindow
from kocrd.system_manager.config.config_module import Config
from kocrd.system_manager.database_manager import DatabaseManager
from kocrd.system_manager.document_manager import DocumentManager
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
import json
import logging

from tool.Sentence_Transformer.numpy._core.tests.test_scalarinherit import C

class MainWindow(QMainWindow, QObject):
    document_updated = pyqtSignal(str, int)
    progress_changed = pyqtSignal(str, int)
    window_size_changed = pyqtSignal(str, int, int)
    splitter_moved = pyqtSignal(float)

    def __init__(self, config_file="config/ui.json", database_manager=None, document_manager=None):
        super().__init__()
        self.config = Config(config_file)
        self.database_manager = database_manager or DatabaseManager()
        self.document_manager = document_manager or DocumentManager()
        self.messages = self.config.language_controller.messages()
        self.message_box = MessageBox(self.config)
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self.init_ui()

    def init_ui(self):
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.monitoring_ui = MonitoringUI(self)
        self.document_ui = DocumentUI(self)
        self.menubar = Menubar(self)
        self.preferences_window = Preferenceswindow(self)
        self.set_window_size()
        self.document_ui.init_ui()
        self.monitoring_ui.init_ui()
        self.menubar.setup_menus()

        self.splitter.addWidget(self.document_ui)
        self.splitter.addWidget(self.monitoring_ui)
        self.setCentralWidget(self.splitter)

        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximumWidth(self.width() * 0.3)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.setVisible(False)

        self.document_updated.connect(self.handle_document_update)
        self.progress_changed.connect(self.handle_progress_change)
        self.window_size_changed.connect(self.handle_window_size_changed)
        self.splitter.splitterMoved.connect(self.handle_splitter_moved)
        self.restore_window_size()

    def restore_window_size(self):
        """창 크기 및 QSplitter 비율을 복원합니다."""
        main_width = self.get_window_setting("W_COL", "MW", "W")
        main_height = self.get_window_setting("W_COL", "MW", "H")
        if main_width and main_height:
            self.resize(main_width, main_height)

        ratio = self.get_splitter_ratio()
        if ratio is not None:
            self.splitter.setSizes([int(main_width * ratio), int(main_width * (1 - ratio))])

    def handle_splitter_moved(self, position, index):
        """QSplitter 이동 시 비율을 저장합니다."""
        ratio = position / self.splitter.width()
        self.set_splitter_ratio(ratio)

    def resizeEvent(self, event):
        """창 크기 변경 시 크기를 저장합니다."""
        size = event.size()
        self.set_window_setting("W_COL", "MW", "W", size.width())
        self.set_window_setting("W_COL", "MW", "H", size.height())
        self.resize_ui_modules(size.width())

    def set_window_size(self):
        width, height = self.get_window_size("main_window_size")
        if width is None or height is None:
            width, height = self.get_window_default_size("main_window_size")
        if width and height:
            self.resize(width, height)
        min_w, min_h = self.get_min_size()
        self.setMinimumSize(min_w, min_h)

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
        if number == 0:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(number)
        print(f"진행률 변경 신호 수신: {text}, {number}")
        # 진행률 업데이트 처리

    @pyqtSlot(str, int, int)
    def handle_window_size_changed(self, name, W, H):
        if name == "main_window_size":
            self.resize(W, H)

    def resize_ui_modules(self, window_width):
        sizes = self.calculate_module_sizes(window_width)
        if sizes:
            self.splitter.setSizes([sizes["document_width"], sizes["monitoring_width"]])

    def closeEvent(self, event):
        self.preferences_window.close()
        event.accept()

    def show_preferences_window(self):
        self.preferences_window.show()

    def delete_document(self, database_manager):
        selected_items = self.document_ui.table_widget.selectedItems()
        if not selected_items:
            self.message_box.show_warning_message(self.config.language_controller.get_message("MSG", "208"))
            return

        selected_row = selected_items[0].row()
        file_name = self.document_ui.table_widget.item(selected_row, 0).text()

        self.execute_action(
            lambda: self._delete_document_action(database_manager, file_name, selected_row),
            confirmation_key="205",
            success_key="206",
            kwargs={"file_name": file_name}
        )

    def _delete_document_action(self, database_manager, file_name, selected_row):
        self.document_ui.table_widget.removeRow(selected_row)
        database_manager.delete_document(file_name)
        logging.info(self.config.language_controller.get_message("MSG", "206").format(file_name=file_name))

    def execute_action(self, action, confirmation_key=None, success_key=None, error_key=None, **kwargs):
        if confirmation_key:
            message = self.config.language_controller.get_message("MSG", confirmation_key).format(**kwargs)
            if not self.message_box.show_confirmation_message(message):
                return

        try:
            result = action() if callable(action) else None
            if success_key:
                message = self.config.language_controller.get_message("MSG", success_key).format(**kwargs)
                self.message_box.show_information_message(message)
            return result
        except Exception as e:
            logging.error(f"Error: {e}")
            message = self.config.language_controller.get_message("ERR", error_key).format(error=e)
            self.message_box.show_error_message(message)

    def get_config_value(self, *keys):
        with open("config/ui.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        value = config
        for key in keys:
            value = value.get(key, {})
        return value

    def get_window_setting(self, setting_type, area=None, key=None):
        if area and key:
            return self.get_config_value("window_settings", setting_type, area, key)
        elif area:
            return self.get_config_value("window_settings", setting_type, area)
        else:
            return self.get_config_value("window_settings", setting_type)

    def set_window_setting(self, setting_type, area, key, value):
        with open("config/ui.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        config["window_settings"][setting_type][area][key] = value
        with open("config/ui.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def set_splitter_ratio(self, ratio):
        self.set_window_setting("W_COL", "D_A", "W_RAT", ratio)
        self.set_window_setting("W_COL", "monitoring_area", "W_RAT", 1 - ratio)

    def get_splitter_ratio(self):
        return self.get_window_setting("W_COL", "D_A", "W_RAT")

    def get_min_size(self):
        min_width = self.get_window_setting("MIN", "W")
        min_height = self.get_window_setting("MIN", "H")
        return min_width if min_width else 500, min_height if min_height else 200

    def get_window_size(self, key):
        width = self.get_window_setting("W_COL", key, "W")
        height = self.get_window_setting("W_COL", key, "H")
        return width, height

    def get_window_default_size(self, key):
        width = self.get_window_setting("DEFAULT", key, "W")
        height = self.get_window_setting("DEFAULT", key, "H")
        return width, height

    def calculate_module_sizes(self, window_width):
        document_ratio = self.get_splitter_ratio()
        monitoring_ratio = 1 - document_ratio
        document_width = int(window_width * document_ratio)
        monitoring_width = int(window_width * monitoring_ratio)
        return {"document_width": document_width, "monitoring_width": monitoring_width}

class MessageBox:
    def __init__(self, config):
        self.config = Config

    def show_error_message(self, message):
        QMessageBox.critical(None, self.config.language_controller.get_message("UI", "012"), message)

    def show_question_message(self, message):
        reply = QMessageBox.question(None, self.config.language_controller.get_message("UI", "010"), message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply

    def show_information_message(self, message):
        QMessageBox.information(None, self.config.language_controller.get_message("UI", "006"), message)

    def show_warning_message(self, message):
        QMessageBox.warning(None, self.config.language_controller.get_message("UI", "011"), message)

    def show_confirmation_message(self, message):
        reply = QMessageBox.question(None, self.config.language_controller.get_message("UI", "011"), message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes