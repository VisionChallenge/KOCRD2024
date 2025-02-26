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

class DocumentUI:
    def __init__(self, main_window, config, database_manager, document_manager):
        super().__init__()
        self.main_window = main_window
        self.config = config
        self.database_manager = database_manager
        self.document_manager = document_manager
        self.table_widget = QTableWidget()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.message_box = MessageBoxUI(config)  # MessageBoxUI 인스턴스 생성
        self.monitoring_ui = MonitoringUI(main_window, config)  # MonitoringUI 인스턴스 생성

    def init_ui(self):
        central_widget = QWidget(self.main_window)
        self.main_window.setCentralWidget(central_widget)
        central_widget.setLayout(QVBoxLayout())

        splitter = QSplitter(central_widget)
        central_widget.layout().addWidget(splitter)

        document_ui_widget = self.create_table_widget()
        splitter.addWidget(document_ui_widget)

        monitoring_ui_widget = self.monitoring_ui
        if isinstance(monitoring_ui_widget, QWidget):
            if monitoring_ui_widget.layout() is None:
                monitoring_layout = QVBoxLayout()
                monitoring_ui_widget.setLayout(monitoring_layout)
            else:
                monitoring_layout = monitoring_ui_widget.layout()
            monitoring_layout.addWidget(self.progress_bar)

            log_display = QTextEdit()
            log_display.setReadOnly(True)
            monitoring_layout.addWidget(log_display)

            # config["monitoring_ui"]["widgets"] 접근 방식 수정
            for widget_config in self.config.get("monitoring_ui", {}).get("widgets", []):
                widget = getattr(self.main_window, widget_config.get("name"))
                monitoring_layout.addWidget(widget)

        else:
            logging.error("Monitoring UI is not a QWidget. Cannot add progress bar.")

        # splitter 크기 설정 방식 개선
        splitter.setSizes([self.main_window.width() * 0.7, self.main_window.width() * 0.3])  # 예시 비율
        logging.info(self.config.coll_text("LOG", "328"))

    def create_table_widget(self):
        """문서 테이블 생성."""
        self.table_widget = QTableWidget()

        self.table_widget.setColumnCount(len(self.config.get("table_columns", [])))  # Config에서 컬럼 정보 가져오기
        self.table_widget.setHorizontalHeaderLabels(self.config.get("table_columns", []))  # Config에서 컬럼 정보 가져오기

        # 헤더 조정
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 컬럼 자동 크기 조정
        header.setStretchLastSection(True)

        return self.table_widget

    def _execute_action(self, action, confirmation_key=None, success_key=None, error_key=None, **kwargs):
        if confirmation_key:
            message = self.config.coll_text("MSG", confirmation_key).format(**kwargs)
            if not self.main_window.show_confirmation_message(message):
                return

        try:
            result = action() if callable(action) else None
            if success_key:
                message = self.config.coll_text("MSG", success_key).format(**kwargs)
                self.main_window.show_information_message(message)
            return result
        except Exception as e:
            logging.error(f"Error: {e}")
            message = self.config.coll_text("ERR", error_key).format(error=e)
            self.main_window.show_error_message(message)

    def clear_table(self):
        """파일 테이블을 초기화합니다."""
        self._execute_action(self._clear_table_action, "202", "203")
    def _clear_table_action(self):
        self.table_widget.setRowCount(0)
        logging.info(self.config.coll_text("MSG", "203"))

    def update_document_info(self, database_manager):
        """선택된 문서의 정보를 업데이트합니다."""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self._show_message_box("208")
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

    def delete_document(self, file_name, database_manager):
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            self.main_window.show_warning_message(self.config.coll_text("MSG", "208"))
            return

        selected_row = selected_items[0].row()
        file_name = self.table_widget.item(selected_row, 0).text()

        message = self.config.coll_text("MSG", "205").format(file_name=file_name)
        if message:
            reply = self.main_window.show_question_message(message)
            if reply == QMessageBox.Yes:
                self._delete_document_action(database_manager, file_name, selected_row)
    def _delete_document_action(self, database_manager, file_name, selected_row):
        self.table_widget.removeRow(selected_row)
        database_manager.delete_document(file_name)
        logging.info(self.config.coll_text("MSG", "206").format(file_name=file_name))
