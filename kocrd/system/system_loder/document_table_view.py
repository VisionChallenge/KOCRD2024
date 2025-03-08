# kocrd/system/system_loder/document_table_view.py
from PyQt5.QtWidgets import QTableWidget, QVBoxLayout, QWidget, QTableWidgetItem, QMessageBox
import logging
import json
import os
from kocrd.system.config.config_module import Config  # ConfigLoader import 추가

config_path = os.path.join(os.path.dirname(__file__), '..', 'managers_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

class DocumentTableView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.message_handler = MessageHandler(Config(config_path))  # MessageHandler 인스턴스 생성
        self.table_widget = QTableWidget()
        self.init_ui()
        logging.info("DocumentTableView initialized.")
    def init_ui(self):
        self.table_widget.setColumnCount(len(self.headers))
        layout = QVBoxLayout()
        layout.addWidget(self.table_widget)
        self.setLayout(layout)
    def add_document(self, document_info):
        row = self.table_widget.rowCount()
        self.table_widget.insertRow(row)
        for col, header in enumerate(self.headers):
            item = QTableWidgetItem(str(document_info.get(header, "")))
            self.table_widget.setItem(row, col, item)
        logging.info(f"Document added to table: {document_info}")
    def sort_table(self):
        self.table_widget.sortItems(0)
        logging.info("Document table sorted.")
    def filter_table(self, criteria):
        """기준에 따라 테이블 필터링."""
        for row in range(self.table_widget.rowCount()):  # 괄호 닫기
            match = all(criteria[key] in self.table_widget.item(row, col).text() for col, key in enumerate(criteria))
            self.table_widget.setRowHidden(row, not match)
        logging.info("Document table filtered.")
    def get_selected_file_names(self):
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self.parent, "선택 오류", self.message_handler.get_message("error.921"))  # 변경
            return None

        selected_file_names = []
        selected_rows = set()
        for item in selected_items:
            selected_rows.add(item.row())

        for row in selected_rows:
            file_name_item = self.table_widget.item(row, 0)
            if file_name_item:
                selected_file_names.append(file_name_item.text())

        return selected_file_names
    def clear_table(self):
        """테이블 초기화."""
        self.table_widget.setRowCount(0)
        logging.info("Document table cleared.")

    def set_headers(self, headers):
        """
        테이블 헤더를 동적으로 설정.

        Args:
            headers (list): 헤더 이름 리스트.
        """
        if not headers or not isinstance(headers, list):
            logging.error("Invalid headers. Expected a non-empty list.")
            return

        self.headers = headers
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        logging.info("Table headers updated.")
