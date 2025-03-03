# kocrd/system/ui.py
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from kocrd.system.ui.document_ui import DocumentUI
from kocrd.system.ui.monitoring_ui import MonitoringUI
from kocrd.system.ui.menubar_ui import Menubar
from kocrd.system.ui.messagebox_ui import MessageBoxUI
from kocrd.system.ui.preferenceswindow_ui import Preferenceswindow
from kocrd.system.config.config_module import Config, UIConfig
from kocrd.system.database_manager import DatabaseManager
from kocrd.system.document_manager import DocumentManager
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

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
        self.messages = self.config.get_messages()
        self.init_ui()

    def init_ui(self):
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.monitoring_ui = MonitoringUI(self, self.config.ui)
        self.document_ui = DocumentUI(self, self.config.ui)
        self.menubar = Menubar(self)
        self.messagebox_ui = MessageBoxUI(self.config)
        self.preferences_window = Preferenceswindow(self)
        self.set_window_size()
        self.document_ui.init_ui()
        self.monitoring_ui.init_ui()
        self.menubar.setup_menus()

        self.splitter.addWidget(self.document_ui)
        self.splitter.addWidget(self.monitoring_ui)
        self.setCentralWidget(self.splitter)

        self.document_updated.connect(self.handle_document_update)
        self.progress_changed.connect(self.handle_progress_change)
        self.config.ui.window_size_changed.connect(self.handle_window_size_changed)
        self.splitter.splitterMoved.connect(self.handle_splitter_moved)
        self.restore_window_size()

    def restore_window_size(self):
        """창 크기 및 QSplitter 비율을 복원합니다."""
        main_width = self.config.ui.get_window_setting("current", "main_window", "width")
        main_height = self.config.ui.get_window_setting("current", "main_window", "height")
        if main_width and main_height:
            self.resize(main_width, main_height)

        ratio = self.config.ui.get_splitter_ratio()
        if ratio is not None:
            self.splitter.setSizes([int(main_width * ratio), int(main_width * (1 - ratio))])

    def handle_splitter_moved(self, position, index):
        """QSplitter 이동 시 비율을 저장합니다."""
        ratio = position / self.splitter.width()
        self.config.ui.set_splitter_ratio(ratio)

    def resizeEvent(self, event):
        """창 크기 변경 시 크기를 저장합니다."""
        size = event.size()
        self.config.ui.set_window_setting("current", "main_window", "width", size.width())
        self.config.ui.set_window_setting("current", "main_window", "height", size.height())
        self.adjust_ui_modules(size.width())

    def restore_splitter_position(self):
        position = self.config.ui.get_splitter_position()
        if position is not None:
            self.splitter.moveSplitter(position, 0)

    def set_window_size(self):
        width, height = self.config.ui.get_window_size("main_window_size")
        if width is None or height is None:
            width, height = self.config.ui.get_window_default_size("main_window_size")
        if width and height:
            self.resize(width, height)
        min_w, min_h = self.config.ui.get_min_size()
        self.setMinimumSize(min_w, min_h)

    def update_document(self, text, number):
        self.document_updated.emit(text, number)

    def update_progress(self, text, number):
        self.progress_changed.emit(text, number)

    @pyqtSlot(str, int)
    def handle_document_update(self, text, number):
        print(f"문서 업데이트 신호 수신: {text}, {number}")
        # 문서 업데이트 처리
    def handle_progress_change(self, text, number):
        print(f"진행률 변경 신호 수신: {text}, {number}")
        # 진행률 업데이트 처리


    @pyqtSlot(str, int, int)
    def handle_window_size_changed(self, name, W, H):
        if name == "main_window_size":
            self.resize(W, H)

    def resize_ui_modules(self, window_width):
        sizes = self.config.ui.calculate_module_sizes(window_width)
        if sizes:
            self.splitter.setSizes([sizes["document_width"], sizes["monitoring_width"]])

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

    def delete_document(self, database_manager):
        selected_items = self.document_ui.table_widget.selectedItems()
        if not selected_items:
            self.show_warning_message(self.config.config.message_handler.get_message("MSG", "208"))
            return

        selected_row = selected_items[0].row()
        file_name = self.document_ui.table_widget.item(selected_row, 0).text()

        self._execute_action(
            lambda: self._delete_document_action(database_manager, file_name, selected_row),
            confirmation_key="205",
            success_key="206",
            kwargs={"file_name": file_name}
        )

    def _delete_document_action(self, database_manager, file_name, selected_row):
        self.document_ui.table_widget.removeRow(selected_row)
        database_manager.delete_document(file_name)
        logging.info(self.config.config.message_handler.get_message("MSG", "206").format(file_name=file_name))

    def execute_action(self, action, confirmation_key=None, success_key=None, error_key=None, **kwargs):
        if confirmation_key:
            message = self.config.config.message_handler.get_message("MSG", confirmation_key).format(**kwargs)
            if not self.main_window.show_confirmation_message(message):
                return

        try:
            result = action() if callable(action) else None
            if success_key:
                message = self.config.config.message_handler.get_message("MSG", success_key).format(**kwargs)
                self.main_window.show_information_message(message)
            return result
        except Exception as e:
            logging.error(f"Error: {e}")
            message = self.config.config.message_handler.get_message("ERR", error_key).format(error=e)
            self.main_window.show_error_message(message)