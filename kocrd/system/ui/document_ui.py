# kocrd/system/ui/document_ui.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog, QTableWidgetItem
from kocrd.system.ui.messagebox_ui import MessageBoxUI
from kocrd.system.document_manager import DocumentManager
from kocrd.system.database_manager import DatabaseManager
from kocrd.system.main_ui import MainWindow
from kocrd.system.config.config_module import Config, LanguageController

class DocumentUI(QWidget):
    def __init__(self, main_window: MainWindow, config: Config, database_manager: DatabaseManager, document_manager: DocumentManager, message_box: MessageBoxUI, LanguageController: LanguageController):
        super().__init__()
        self.main_window = main_window
        self.config = config
        self.database_manager = database_manager
        self.document_manager = document_manager
        self.message_handler = LanguageController
        self.message_box = message_box
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.create_table_widget())
        self.setLayout(layout)

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(len(self.config.get("table_columns", [])))
        self.table_widget.setHorizontalHeaderLabels([col["name"] for col in self.config.get("table_columns", [])])

        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setStretchLastSection(True)

        return self.table_widget

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        self.document_manager.clear_table()
        logging.info(self.message_handler.get_message("MSG", "203"))

    def update_document_info(self):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.document_manager.get_selected_items()
        if not selected_items:
            self.message_box.show_warning_message(self.message_handler.get_message("MSG", "208"))
            return

        selected_row = selected_items[0].row()
        current_file_name = self.document_manager.get_item_text(selected_row, 0)
        new_type, ok = QInputDialog.getText(self, "문서 유형 수정", f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            self.document_manager.update_document_type(current_file_name, new_type, selected_row)

