# kocrd/system/ui/document_ui.py
import logging
import json
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QTextEdit, QProgressBar, QTableWidget, QHeaderView, QMessageBox, QInputDialog, QTableWidgetItem
from PyQt5.QtCore import Qt
from kocrd.system.config.config import Config
from kocrd.system.ui.monitoring_ui import MonitoringUI
from kocrd.system.ui.messagebox_ui import MessageBoxUI
from kocrd.system.document_manager import DocumentManager
from kocrd.system.database_manager import DatabaseManager
from kocrd.system.ui import MainWindow
class DocumentUI(QWidget):
    def __init__(self, main_window, config, database_manager, document_manager):
        super().__init__()
        self.main_window = 
        self.config = config
        self.database_manager = database_manager
        self.document_manager = document_manager
        self.table_widget = QTableWidget()
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
        self._execute_action(self._clear_table_action, "202", "203")

    def _clear_table_action(self):
        self.table_widget.setRowCount(0)
        logging.info(self.message_box.get_message("MSG", "203"))

    def update_document_info(self, database_manager):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self.main_window.show_warning_message(self.config.config.message_handler.get_message("MSG", "208"))
            return

        selected_row = selected_items[0].row()
        current_file_name = self.table_widget.item(selected_row, 0).text()
        new_type, ok = QInputDialog.getText(self.main_window, "문서 유형 수정", f"{current_file_name}의 새로운 문서 유형을 입력하세요:")
        if ok and new_type:
            self._execute_action(
                lambda: self._update_document_type(database_manager, current_file_name, new_type, selected_row),
                success_key="204",
                error_key="205"
            )

    def _update_document_type(self, database_manager, current_file_name, new_type, selected_row):
        database_manager.update_document_type(current_file_name, new_type)
        self.table_widget.setItem(selected_row, 1, QTableWidgetItem(new_type))
        logging.info(f"Updated document type for {current_file_name} to {new_type}")

